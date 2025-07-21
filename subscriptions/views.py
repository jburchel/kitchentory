"""
Subscription views for handling Stripe checkout and subscription management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
import stripe
import json
import logging

from .models import SubscriptionPlan, Subscription, BillingHistory
from .stripe_config import StripeService, StripeConfig
from .services import SubscriptionService
from .decorators import subscription_required

logger = logging.getLogger(__name__)


@login_required
def subscription_dashboard(request):
    """
    Main subscription dashboard showing current plan and usage.
    """
    user = request.user
    plan = user.get_subscription_plan()
    subscription = getattr(user, 'subscription', None)
    
    context = {
        'current_plan': plan,
        'subscription': subscription,
        'has_active_subscription': subscription and subscription.is_active,
        'usage_data': request.subscription.get('usage', {}) if hasattr(request, 'subscription') else {},
        'available_plans': SubscriptionPlan.objects.filter(is_active=True).exclude(tier='free'),
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    
    return render(request, 'subscriptions/dashboard.html', context)


@login_required
def upgrade_plans(request):
    """
    Show available upgrade plans.
    """
    user = request.user
    current_plan = user.get_subscription_plan()
    
    # Get available upgrade options
    upgrade_options = SubscriptionService.get_upgrade_options(user)
    
    context = {
        'current_plan': current_plan,
        'upgrade_options': upgrade_options,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    
    return render(request, 'subscriptions/upgrade.html', context)


@login_required
@require_POST
def create_checkout_session(request):
    """
    Create a Stripe Checkout session for subscription.
    """
    try:
        data = json.loads(request.body)
        price_lookup_key = data.get('price_lookup_key')
        billing_period = data.get('billing_period', 'monthly')
        tier = data.get('tier')
        
        if not tier or tier not in ['premium', 'pro']:
            return JsonResponse({'error': 'Invalid subscription tier'}, status=400)
        
        # Get the price ID
        price_id = StripeConfig.get_price_id(tier, billing_period)
        if not price_id:
            return JsonResponse({'error': 'Invalid pricing configuration'}, status=400)
        
        # Build URLs
        success_url = request.build_absolute_uri(
            reverse('subscriptions:checkout_success') + '?session_id={CHECKOUT_SESSION_ID}'
        )
        cancel_url = request.build_absolute_uri(reverse('subscriptions:checkout_cancel'))
        
        # Create checkout session
        session = StripeService.create_checkout_session(
            user=request.user,
            price_id=price_id,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'tier': tier,
                'billing_period': billing_period,
            }
        )
        
        if not session:
            return JsonResponse({'error': 'Failed to create checkout session'}, status=500)
        
        return JsonResponse({'checkout_url': session.url})
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        return JsonResponse({'error': 'An error occurred'}, status=500)


@login_required
def checkout_success(request):
    """
    Handle successful checkout redirect.
    """
    session_id = request.GET.get('session_id')
    
    if session_id:
        try:
            # Retrieve the checkout session
            session = stripe.checkout.Session.retrieve(session_id)
            
            if session.payment_status == 'paid':
                messages.success(
                    request,
                    "Thank you! Your subscription has been activated. "
                    "You now have access to all premium features."
                )
            else:
                messages.info(
                    request,
                    "Your subscription is being processed. "
                    "You'll receive a confirmation email shortly."
                )
                
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving checkout session: {str(e)}")
            messages.warning(
                request,
                "There was an issue verifying your payment. "
                "Please contact support if you continue to experience problems."
            )
    
    return redirect('subscriptions:dashboard')


@login_required 
def checkout_cancel(request):
    """
    Handle cancelled checkout.
    """
    messages.info(
        request,
        "Checkout was cancelled. You can upgrade anytime from your dashboard."
    )
    return redirect('subscriptions:dashboard')


@login_required
def billing_history(request):
    """
    Show user's billing history.
    """
    user = request.user
    billing_records = BillingHistory.objects.filter(
        user=user
    ).order_by('-created_at')[:50]  # Last 50 records
    
    context = {
        'billing_records': billing_records,
    }
    
    return render(request, 'subscriptions/billing_history.html', context)


@login_required
def manage_subscription(request):
    """
    Subscription management page with customer portal link.
    """
    user = request.user
    subscription = getattr(user, 'subscription', None)
    
    if not subscription or not user.stripe_customer_id:
        messages.error(request, "No active subscription found.")
        return redirect('subscriptions:dashboard')
    
    context = {
        'subscription': subscription,
        'can_cancel': subscription.is_active,
    }
    
    return render(request, 'subscriptions/manage.html', context)


@login_required
@require_POST
def create_customer_portal_session(request):
    """
    Create a Stripe Customer Portal session.
    """
    user = request.user
    
    if not user.stripe_customer_id:
        return JsonResponse({'error': 'No Stripe customer found'}, status=400)
    
    return_url = request.build_absolute_uri(reverse('subscriptions:dashboard'))
    
    session = StripeService.create_customer_portal_session(
        customer_id=user.stripe_customer_id,
        return_url=return_url
    )
    
    if not session:
        return JsonResponse({'error': 'Failed to create portal session'}, status=500)
    
    return JsonResponse({'portal_url': session.url})


@login_required
@require_POST
def cancel_subscription_view(request):
    """
    Cancel user's subscription.
    """
    user = request.user
    subscription = getattr(user, 'subscription', None)
    
    if not subscription or not subscription.is_active:
        return JsonResponse({'error': 'No active subscription found'}, status=400)
    
    data = json.loads(request.body) if request.body else {}
    immediately = data.get('immediately', False)
    
    # Cancel in Stripe
    if subscription.stripe_subscription_id:
        stripe_subscription = StripeService.cancel_subscription(
            subscription_id=subscription.stripe_subscription_id,
            at_period_end=not immediately
        )
        
        if not stripe_subscription:
            return JsonResponse({'error': 'Failed to cancel subscription'}, status=500)
    
    # Update local subscription
    SubscriptionService.cancel_subscription(subscription, immediately=immediately)
    
    if immediately:
        messages.success(request, "Your subscription has been cancelled.")
    else:
        messages.info(request, "Your subscription will be cancelled at the end of the current period.")
    
    return JsonResponse({'success': True})


@csrf_exempt
def stripe_webhook(request):
    """
    Handle Stripe webhooks.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload in webhook: {str(e)}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in webhook: {str(e)}")
        return HttpResponse(status=400)
    
    # Handle the event
    try:
        if event['type'] == 'checkout.session.completed':
            handle_checkout_session_completed(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_invoice_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_invoice_payment_failed(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        else:
            logger.info(f"Unhandled webhook event type: {event['type']}")
    
    except Exception as e:
        logger.error(f"Error handling webhook event {event['type']}: {str(e)}")
        return HttpResponse(status=500)
    
    return HttpResponse(status=200)


def handle_checkout_session_completed(session):
    """Handle completed checkout session."""
    user_id = session['metadata'].get('user_id')
    if not user_id:
        logger.error("No user_id in checkout session metadata")
        return
    
    try:
        from accounts.models import User
        user = User.objects.get(id=user_id)
        
        # Get the subscription from Stripe
        subscription_id = session['subscription']
        stripe_subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Get the plan based on the price
        price_id = stripe_subscription['items']['data'][0]['price']['id']
        tier = None
        billing_period = 'monthly'
        
        # Map price ID back to tier (this could be improved with metadata)
        for plan_tier, price_config in StripeConfig.PRODUCTS.items():
            if price_id == price_config['monthly_price_id']:
                tier = plan_tier
                billing_period = 'monthly'
                break
            elif price_id == price_config['yearly_price_id']:
                tier = plan_tier
                billing_period = 'yearly'
                break
        
        if tier:
            plan = SubscriptionPlan.objects.get(tier=tier)
            
            # Create or update subscription
            subscription = SubscriptionService.create_subscription(
                user=user,
                plan=plan,
                billing_period=billing_period,
                trial_days=0  # No trial for direct purchases
            )
            
            # Update with Stripe data
            subscription.stripe_subscription_id = subscription_id
            subscription.stripe_customer_id = session['customer']
            subscription.save()
            
            logger.info(f"Created subscription for user {user.email}: {tier} ({billing_period})")
            
    except Exception as e:
        logger.error(f"Error processing checkout session completion: {str(e)}")


def handle_invoice_payment_succeeded(invoice):
    """Handle successful invoice payment."""
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        SubscriptionService.process_payment_success(
            subscription=subscription,
            amount=invoice['amount_paid'] / 100,  # Convert cents to dollars
            stripe_data={
                'invoice_id': invoice['id'],
                'payment_intent_id': invoice.get('payment_intent'),
            }
        )
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found for Stripe subscription {subscription_id}")


def handle_invoice_payment_failed(invoice):
    """Handle failed invoice payment."""
    subscription_id = invoice.get('subscription')
    if not subscription_id:
        return
    
    try:
        subscription = Subscription.objects.get(stripe_subscription_id=subscription_id)
        SubscriptionService.process_payment_failure(
            subscription=subscription,
            amount=invoice['amount_due'] / 100,  # Convert cents to dollars
            reason="Payment failed",
            stripe_data={
                'invoice_id': invoice['id'],
            }
        )
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found for Stripe subscription {subscription_id}")


def handle_subscription_updated(stripe_subscription):
    """Handle subscription updates from Stripe."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        
        # Update status based on Stripe subscription status
        status_mapping = {
            'active': 'active',
            'past_due': 'past_due',
            'canceled': 'canceled',
            'unpaid': 'past_due',
        }
        
        new_status = status_mapping.get(stripe_subscription['status'], 'unknown')
        if new_status != subscription.status:
            subscription.status = new_status
            subscription.save()
            
            # Update user cache
            SubscriptionService.update_user_subscription_cache(subscription.user, subscription)
            
            logger.info(f"Updated subscription status: {subscription.id} -> {new_status}")
            
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found for Stripe subscription {stripe_subscription['id']}")


def handle_subscription_deleted(stripe_subscription):
    """Handle subscription deletion from Stripe."""
    try:
        subscription = Subscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        
        SubscriptionService.cancel_subscription(subscription, immediately=True)
        logger.info(f"Cancelled subscription due to Stripe deletion: {subscription.id}")
        
    except Subscription.DoesNotExist:
        logger.error(f"Subscription not found for Stripe subscription {stripe_subscription['id']}")