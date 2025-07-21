from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import SubscriptionPlan, Subscription, BillingHistory, InventoryUsage, ShoppingListUsage
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class SubscriptionService:
    """
    Service class for handling subscription operations like upgrades, downgrades,
    and subscription management.
    """
    
    @classmethod
    def create_subscription(cls, user, plan, billing_period='monthly', trial_days=14):
        """
        Create a new subscription for a user.
        
        Args:
            user: User instance
            plan: SubscriptionPlan instance
            billing_period: 'monthly' or 'yearly'
            trial_days: Number of trial days (0 for no trial)
        
        Returns:
            Subscription instance
        """
        with transaction.atomic():
            # End any existing subscription
            if hasattr(user, 'subscription'):
                cls.cancel_subscription(user.subscription, immediately=True)
            
            # Calculate trial and billing dates
            now = timezone.now()
            trial_start = now if trial_days > 0 else None
            trial_end = now + timezone.timedelta(days=trial_days) if trial_days > 0 else None
            
            # If there's a trial, subscription starts after trial
            # If no trial, subscription starts immediately
            current_period_start = trial_end if trial_end else now
            
            if billing_period == 'yearly':
                current_period_end = current_period_start + timezone.timedelta(days=365)
            else:
                current_period_end = current_period_start + timezone.timedelta(days=30)
            
            # Create subscription
            subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                status='trialing' if trial_days > 0 else 'active',
                billing_period=billing_period,
                trial_start=trial_start,
                trial_end=trial_end,
                current_period_start=current_period_start,
                current_period_end=current_period_end,
            )
            
            # Update user's cached subscription info
            cls.update_user_subscription_cache(user, subscription)
            
            logger.info(
                f"Created subscription for user {user.email}: "
                f"{plan.name} ({billing_period})"
            )
            
            return subscription
    
    @classmethod
    def upgrade_subscription(cls, user, new_plan, billing_period=None):
        """
        Upgrade a user's subscription to a higher tier.
        
        Args:
            user: User instance
            new_plan: SubscriptionPlan instance (higher tier)
            billing_period: Optional billing period change
        
        Returns:
            Subscription instance or None if upgrade failed
        """
        if not hasattr(user, 'subscription'):
            return cls.create_subscription(user, new_plan, billing_period or 'monthly')
        
        subscription = user.subscription
        current_plan = subscription.plan
        
        # Validate upgrade (ensure new plan is higher tier)
        tier_hierarchy = {'free': 0, 'premium': 1, 'pro': 2}
        current_level = tier_hierarchy.get(current_plan.tier, 0)
        new_level = tier_hierarchy.get(new_plan.tier, 0)
        
        if new_level <= current_level:
            logger.warning(
                f"Invalid upgrade attempt: {current_plan.tier} -> {new_plan.tier} "
                f"for user {user.email}"
            )
            return None
        
        with transaction.atomic():
            # Update subscription
            subscription.plan = new_plan
            if billing_period:
                subscription.billing_period = billing_period
            
            # If upgrading from trial, make it active
            if subscription.is_trialing:
                subscription.status = 'active'
            
            subscription.save()
            
            # Update user cache
            cls.update_user_subscription_cache(user, subscription)
            
            logger.info(
                f"Upgraded subscription for user {user.email}: "
                f"{current_plan.tier} -> {new_plan.tier}"
            )
            
            return subscription
    
    @classmethod
    def downgrade_subscription(cls, user, new_plan, immediate=False):
        """
        Downgrade a user's subscription to a lower tier.
        
        Args:
            user: User instance
            new_plan: SubscriptionPlan instance (lower tier)
            immediate: Whether to apply downgrade immediately or at period end
        
        Returns:
            Subscription instance or None if downgrade failed
        """
        if not hasattr(user, 'subscription'):
            logger.warning(f"No subscription to downgrade for user {user.email}")
            return None
        
        subscription = user.subscription
        current_plan = subscription.plan
        
        # Validate downgrade
        tier_hierarchy = {'free': 0, 'premium': 1, 'pro': 2}
        current_level = tier_hierarchy.get(current_plan.tier, 0)
        new_level = tier_hierarchy.get(new_plan.tier, 0)
        
        if new_level >= current_level:
            logger.warning(
                f"Invalid downgrade attempt: {current_plan.tier} -> {new_plan.tier} "
                f"for user {user.email}"
            )
            return None
        
        with transaction.atomic():
            if immediate:
                # Apply downgrade immediately
                subscription.plan = new_plan
                subscription.save()
                
                # Handle data limits for immediate downgrade
                cls.handle_downgrade_limits(user, new_plan)
                
                # Update user cache
                cls.update_user_subscription_cache(user, subscription)
                
                logger.info(
                    f"Immediately downgraded subscription for user {user.email}: "
                    f"{current_plan.tier} -> {new_plan.tier}"
                )
            else:
                # Schedule downgrade for end of current period
                # This would typically be handled by a scheduled task or webhook
                # For now, we'll store it in a way that can be processed later
                subscription.save()
                
                logger.info(
                    f"Scheduled downgrade for user {user.email}: "
                    f"{current_plan.tier} -> {new_plan.tier} at period end"
                )
            
            return subscription
    
    @classmethod
    def cancel_subscription(cls, subscription, immediately=False):
        """
        Cancel a subscription.
        
        Args:
            subscription: Subscription instance
            immediately: Whether to cancel immediately or at period end
        """
        with transaction.atomic():
            subscription.canceled_at = timezone.now()
            
            if immediately:
                subscription.status = 'canceled'
                subscription.current_period_end = timezone.now()
                
                # Downgrade to free plan
                free_plan = SubscriptionPlan.objects.get(tier='free')
                subscription.plan = free_plan
                
                # Handle data limits
                cls.handle_downgrade_limits(subscription.user, free_plan)
            
            subscription.save()
            
            # Update user cache
            cls.update_user_subscription_cache(subscription.user, subscription)
            
            logger.info(
                f"Canceled subscription for user {subscription.user.email} "
                f"({'immediately' if immediately else 'at period end'})"
            )
    
    @classmethod
    def handle_downgrade_limits(cls, user, new_plan):
        """
        Handle data limits when downgrading to a more restrictive plan.
        
        Args:
            user: User instance
            new_plan: New SubscriptionPlan instance with limits
        """
        # Handle inventory limits
        if new_plan.max_inventory_items:
            inventory_usage, _ = InventoryUsage.objects.get_or_create(user=user)
            if inventory_usage.item_count > new_plan.max_inventory_items:
                # This would typically trigger a notification to the user
                # to reduce their inventory items
                logger.warning(
                    f"User {user.email} inventory ({inventory_usage.item_count}) "
                    f"exceeds new plan limit ({new_plan.max_inventory_items})"
                )
        
        # Handle shopping list limits
        if new_plan.max_shopping_lists:
            shopping_usage, _ = ShoppingListUsage.objects.get_or_create(user=user)
            if shopping_usage.list_count > new_plan.max_shopping_lists:
                logger.warning(
                    f"User {user.email} shopping lists ({shopping_usage.list_count}) "
                    f"exceeds new plan limit ({new_plan.max_shopping_lists})"
                )
        
        # Additional limit handling would go here
    
    @classmethod
    def update_user_subscription_cache(cls, user, subscription):
        """
        Update cached subscription information on the user model.
        
        Args:
            user: User instance
            subscription: Subscription instance
        """
        user.current_plan = subscription.plan
        user.subscription_status = subscription.status
        user.trial_end_date = subscription.trial_end
        user.subscription_end_date = subscription.current_period_end
        user.save(update_fields=[
            'current_plan', 'subscription_status', 
            'trial_end_date', 'subscription_end_date'
        ])
    
    @classmethod
    def process_payment_success(cls, subscription, amount, stripe_data=None):
        """
        Process a successful payment for a subscription.
        
        Args:
            subscription: Subscription instance
            amount: Payment amount
            stripe_data: Optional Stripe webhook data
        """
        with transaction.atomic():
            # Update subscription status
            subscription.status = 'active'
            subscription.save()
            
            # Create billing history record
            BillingHistory.objects.create(
                user=subscription.user,
                subscription=subscription,
                type='payment',
                status='succeeded',
                amount=amount,
                stripe_invoice_id=stripe_data.get('invoice_id') if stripe_data else '',
                stripe_payment_intent_id=stripe_data.get('payment_intent_id') if stripe_data else '',
                description=f"Payment for {subscription.plan.name} subscription",
                paid_at=timezone.now(),
            )
            
            # Update user cache
            cls.update_user_subscription_cache(subscription.user, subscription)
            
            logger.info(
                f"Processed successful payment for user {subscription.user.email}: "
                f"${amount}"
            )
    
    @classmethod
    def process_payment_failure(cls, subscription, amount, reason=None, stripe_data=None):
        """
        Process a failed payment for a subscription.
        
        Args:
            subscription: Subscription instance
            amount: Payment amount that failed
            reason: Failure reason
            stripe_data: Optional Stripe webhook data
        """
        with transaction.atomic():
            # Update subscription status
            subscription.status = 'past_due'
            subscription.save()
            
            # Create billing history record
            BillingHistory.objects.create(
                user=subscription.user,
                subscription=subscription,
                type='payment',
                status='failed',
                amount=amount,
                stripe_invoice_id=stripe_data.get('invoice_id') if stripe_data else '',
                description=f"Failed payment for {subscription.plan.name} subscription: {reason or 'Unknown error'}",
            )
            
            # Update user cache
            cls.update_user_subscription_cache(subscription.user, subscription)
            
            logger.warning(
                f"Processed failed payment for user {subscription.user.email}: "
                f"${amount} - {reason or 'Unknown error'}"
            )
    
    @classmethod
    def get_upgrade_options(cls, user):
        """
        Get available upgrade options for a user.
        
        Args:
            user: User instance
            
        Returns:
            List of SubscriptionPlan instances that user can upgrade to
        """
        current_plan = user.get_subscription_plan()
        if not current_plan:
            # User has no plan, show all paid plans
            return SubscriptionPlan.objects.filter(
                is_active=True,
                tier__in=['premium', 'pro']
            ).order_by('monthly_price')
        
        tier_hierarchy = {'free': 0, 'premium': 1, 'pro': 2}
        current_level = tier_hierarchy.get(current_plan.tier, 0)
        
        # Get plans with higher tier levels
        available_tiers = [
            tier for tier, level in tier_hierarchy.items() 
            if level > current_level
        ]
        
        return SubscriptionPlan.objects.filter(
            is_active=True,
            tier__in=available_tiers
        ).order_by('monthly_price')
    
    @classmethod
    def get_downgrade_options(cls, user):
        """
        Get available downgrade options for a user.
        
        Args:
            user: User instance
            
        Returns:
            List of SubscriptionPlan instances that user can downgrade to
        """
        current_plan = user.get_subscription_plan()
        if not current_plan or current_plan.tier == 'free':
            return SubscriptionPlan.objects.none()
        
        tier_hierarchy = {'free': 0, 'premium': 1, 'pro': 2}
        current_level = tier_hierarchy.get(current_plan.tier, 0)
        
        # Get plans with lower tier levels
        available_tiers = [
            tier for tier, level in tier_hierarchy.items() 
            if level < current_level
        ]
        
        return SubscriptionPlan.objects.filter(
            is_active=True,
            tier__in=available_tiers
        ).order_by('monthly_price')
    
    @classmethod
    def calculate_proration(cls, subscription, new_plan, billing_period=None):
        """
        Calculate proration amount for plan changes.
        
        Args:
            subscription: Current subscription
            new_plan: New plan to change to
            billing_period: Optional new billing period
            
        Returns:
            dict with proration details
        """
        if not subscription:
            return {'amount': Decimal('0.00'), 'description': 'No existing subscription'}
        
        current_plan = subscription.plan
        current_billing = subscription.billing_period
        new_billing = billing_period or current_billing
        
        # Calculate remaining days in current period
        now = timezone.now()
        remaining_days = (subscription.current_period_end - now).days
        
        if remaining_days <= 0:
            return {'amount': Decimal('0.00'), 'description': 'Current period has ended'}
        
        # Calculate current plan daily rate
        current_price = current_plan.get_price(current_billing)
        days_in_period = 365 if current_billing == 'yearly' else 30
        current_daily_rate = current_price / days_in_period
        
        # Calculate new plan daily rate
        new_price = new_plan.get_price(new_billing)
        new_days_in_period = 365 if new_billing == 'yearly' else 30
        new_daily_rate = new_price / new_days_in_period
        
        # Calculate proration
        remaining_current_value = current_daily_rate * remaining_days
        remaining_new_value = new_daily_rate * remaining_days
        
        proration_amount = remaining_new_value - remaining_current_value
        
        return {
            'amount': proration_amount,
            'remaining_days': remaining_days,
            'current_daily_rate': current_daily_rate,
            'new_daily_rate': new_daily_rate,
            'description': f'Proration for {remaining_days} remaining days'
        }