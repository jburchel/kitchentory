from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from .models import SubscriptionPlan, RecipeSearchUsage, InventoryUsage, ShoppingListUsage


def subscription_required(tier='premium'):
    """
    Decorator that requires a user to have at least the specified subscription tier.
    
    Args:
        tier (str): Minimum required tier ('premium' or 'pro')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            # Get user's current plan
            plan = user.get_subscription_plan()
            
            if not plan:
                messages.error(request, "Unable to determine your subscription plan.")
                return redirect('subscriptions:upgrade')
            
            # Check if user has required tier
            tier_hierarchy = {'free': 0, 'premium': 1, 'pro': 2}
            user_tier_level = tier_hierarchy.get(plan.tier, 0)
            required_tier_level = tier_hierarchy.get(tier, 1)
            
            if user_tier_level < required_tier_level:
                messages.info(
                    request, 
                    f"This feature requires a {tier.title()} subscription. "
                    f"Upgrade your plan to access this feature."
                )
                return redirect('subscriptions:upgrade')
            
            # Check if subscription is active
            if hasattr(user, 'subscription') and not user.subscription.is_active:
                messages.warning(
                    request,
                    "Your subscription has expired. Please update your payment method "
                    "or resubscribe to continue using premium features."
                )
                return redirect('subscriptions:manage')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def feature_required(feature_name):
    """
    Decorator that requires a user to have access to a specific feature.
    
    Args:
        feature_name (str): Name of the feature (e.g., 'recipe_matching', 'analytics')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            if not user.can_use_feature(feature_name):
                feature_display_names = {
                    'recipe_matching': 'Recipe Matching',
                    'advanced_matching': 'Advanced Recipe Matching',
                    'meal_planning': 'Meal Planning',
                    'nutrition_tracking': 'Nutrition Tracking',
                    'analytics': 'Analytics Dashboard',
                    'advanced_analytics': 'Advanced Analytics',
                    'export': 'Data Export',
                    'api_access': 'API Access',
                    'ocr_receipts': 'Receipt Scanning',
                    'voice_input': 'Voice Input',
                }
                
                feature_display = feature_display_names.get(
                    feature_name, 
                    feature_name.replace('_', ' ').title()
                )
                
                messages.info(
                    request,
                    f"{feature_display} is not available with your current plan. "
                    f"Upgrade to access this feature."
                )
                return redirect('subscriptions:upgrade')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def usage_limit_required(limit_type, redirect_to_upgrade=True):
    """
    Decorator that checks usage limits before allowing access.
    
    Args:
        limit_type (str): Type of limit to check ('inventory', 'recipe_search', 'shopping_list')
        redirect_to_upgrade (bool): Whether to redirect to upgrade page or show error
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            
            if limit_type == 'inventory':
                usage, _ = InventoryUsage.objects.get_or_create(user=user)
                if not usage.can_add_item():
                    plan = user.get_subscription_plan()
                    message = (
                        f"You've reached your inventory limit of {plan.max_inventory_items} items. "
                        f"Upgrade to Premium for unlimited inventory tracking."
                    )
                    messages.warning(request, message)
                    
                    if redirect_to_upgrade:
                        return redirect('subscriptions:upgrade')
                    elif request.headers.get('content-type') == 'application/json':
                        return JsonResponse({'error': message}, status=403)
                    else:
                        return redirect('inventory:dashboard')
            
            elif limit_type == 'recipe_search':
                if not RecipeSearchUsage.can_search(user):
                    plan = user.get_subscription_plan()
                    today_count = RecipeSearchUsage.get_today_count(user)
                    message = (
                        f"You've used {today_count} of {plan.max_recipes_per_day} daily recipe searches. "
                        f"Upgrade to Premium for unlimited searches."
                    )
                    messages.warning(request, message)
                    
                    if redirect_to_upgrade:
                        return redirect('subscriptions:upgrade')
                    elif request.headers.get('content-type') == 'application/json':
                        return JsonResponse({'error': message}, status=403)
                    else:
                        return redirect('recipes:dashboard')
            
            elif limit_type == 'shopping_list':
                usage, _ = ShoppingListUsage.objects.get_or_create(user=user)
                if not usage.can_create_list():
                    plan = user.get_subscription_plan()
                    message = (
                        f"You've reached your shopping list limit of {plan.max_shopping_lists}. "
                        f"Upgrade to Premium for unlimited shopping lists."
                    )
                    messages.warning(request, message)
                    
                    if redirect_to_upgrade:
                        return redirect('subscriptions:upgrade')
                    elif request.headers.get('content-type') == 'application/json':
                        return JsonResponse({'error': message}, status=403)
                    else:
                        return redirect('shopping:dashboard')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def ajax_subscription_required(tier='premium'):
    """
    Decorator for AJAX views that requires a subscription tier.
    Returns JSON response instead of redirecting.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user = request.user
            plan = user.get_subscription_plan()
            
            if not plan:
                return JsonResponse({
                    'error': 'Unable to determine subscription plan',
                    'upgrade_required': True
                }, status=403)
            
            tier_hierarchy = {'free': 0, 'premium': 1, 'pro': 2}
            user_tier_level = tier_hierarchy.get(plan.tier, 0)
            required_tier_level = tier_hierarchy.get(tier, 1)
            
            if user_tier_level < required_tier_level:
                return JsonResponse({
                    'error': f'This feature requires a {tier.title()} subscription',
                    'upgrade_required': True,
                    'current_tier': plan.tier,
                    'required_tier': tier
                }, status=403)
            
            # Check if subscription is active
            if hasattr(user, 'subscription') and not user.subscription.is_active:
                return JsonResponse({
                    'error': 'Your subscription has expired',
                    'subscription_expired': True
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def track_usage(usage_type):
    """
    Decorator that tracks usage for analytics and limit enforcement.
    
    Args:
        usage_type (str): Type of usage to track ('recipe_search', 'export', etc.)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user if request.user.is_authenticated else None
            
            # Execute the view first
            response = view_func(request, *args, **kwargs)
            
            # Track usage if user is authenticated and view was successful
            if user and hasattr(response, 'status_code') and response.status_code == 200:
                if usage_type == 'recipe_search':
                    RecipeSearchUsage.increment_search(user)
                
                # Add other usage tracking as needed
                elif usage_type == 'export':
                    # Could track export usage here
                    pass
            
            return response
        return _wrapped_view
    return decorator


def trial_access_allowed(view_func):
    """
    Decorator that allows access during trial period even for premium features.
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        
        # Check if user is in trial period
        if hasattr(user, 'subscription') and user.subscription.is_trialing:
            return view_func(request, *args, **kwargs)
        
        # Otherwise, normal subscription checks apply
        plan = user.get_subscription_plan()
        if plan and plan.tier == 'free':
            messages.info(
                request,
                "Your trial period has ended. Upgrade to continue using premium features."
            )
            return redirect('subscriptions:upgrade')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view