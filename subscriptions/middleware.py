from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from .models import SubscriptionPlan, InventoryUsage, RecipeSearchUsage, ShoppingListUsage


class SubscriptionMiddleware:
    """
    Middleware that adds subscription context to requests and handles
    subscription-related functionality across the application.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # Paths that don't require subscription checks
        self.exempt_paths = [
            '/admin/',
            '/accounts/login/',
            '/accounts/logout/',
            '/accounts/signup/',
            '/subscriptions/',
            '/static/',
            '/media/',
            '/api/webhooks/',
        ]
        
        # Paths that should redirect expired users
        self.premium_paths = [
            '/recipes/discover/',
            '/analytics/',
            '/export/',
            '/api/recipes/match/',
        ]

    def __call__(self, request):
        # Add subscription context to request
        self.add_subscription_context(request)
        
        # Check for expired subscriptions
        if request.user.is_authenticated:
            self.handle_expired_subscription(request)
        
        response = self.get_response(request)
        return response

    def add_subscription_context(self, request):
        """Add subscription-related context to the request."""
        if request.user.is_authenticated:
            # Get or create usage tracking records
            inventory_usage, _ = InventoryUsage.objects.get_or_create(user=request.user)
            shopping_usage, _ = ShoppingListUsage.objects.get_or_create(user=request.user)
            
            # Get today's recipe search count
            recipe_usage_count = RecipeSearchUsage.get_today_count(request.user)
            
            # Get user's subscription plan
            plan = request.user.get_subscription_plan()
            
            # Add subscription context
            request.subscription = {
                'plan': plan,
                'tier': plan.tier if plan else 'free',
                'is_premium': request.user.has_premium_features(),
                'is_pro': request.user.has_pro_features(),
                'usage': {
                    'inventory_count': inventory_usage.item_count,
                    'inventory_limit': plan.max_inventory_items if plan else 50,
                    'inventory_can_add': inventory_usage.can_add_item(),
                    'recipe_searches_today': recipe_usage_count,
                    'recipe_search_limit': plan.max_recipes_per_day if plan else 5,
                    'recipe_can_search': RecipeSearchUsage.can_search(request.user),
                    'shopping_list_count': shopping_usage.list_count,
                    'shopping_list_limit': plan.max_shopping_lists if plan else 1,
                    'shopping_list_can_create': shopping_usage.can_create_list(),
                },
                'features': {
                    'recipe_matching': plan.has_recipe_matching if plan else False,
                    'advanced_matching': plan.has_advanced_matching if plan else False,
                    'meal_planning': plan.has_meal_planning if plan else False,
                    'nutrition_tracking': plan.has_nutrition_tracking if plan else False,
                    'analytics': plan.has_analytics if plan else False,
                    'advanced_analytics': plan.has_advanced_analytics if plan else False,
                    'export': plan.has_export if plan else False,
                    'api_access': plan.has_api_access if plan else False,
                    'ocr_receipts': plan.has_ocr_receipts if plan else False,
                    'voice_input': plan.has_voice_input if plan else False,
                    'priority_support': plan.has_priority_support if plan else False,
                }
            }
            
            # Check if subscription is expired or expiring soon
            if hasattr(request.user, 'subscription'):
                subscription = request.user.subscription
                now = timezone.now()
                
                request.subscription.update({
                    'is_active': subscription.is_active,
                    'is_trialing': subscription.is_trialing,
                    'is_expired': not subscription.is_active,
                    'expires_soon': (
                        subscription.current_period_end and 
                        subscription.current_period_end - now < timezone.timedelta(days=3)
                    ),
                    'trial_ends_soon': (
                        subscription.trial_end and
                        subscription.trial_end - now < timezone.timedelta(days=2)
                    ),
                    'current_period_end': subscription.current_period_end,
                    'trial_end': subscription.trial_end,
                })
        else:
            # Default context for non-authenticated users
            request.subscription = {
                'plan': None,
                'tier': 'free',
                'is_premium': False,
                'is_pro': False,
                'usage': {
                    'inventory_count': 0,
                    'inventory_limit': 50,
                    'inventory_can_add': False,
                    'recipe_searches_today': 0,
                    'recipe_search_limit': 5,
                    'recipe_can_search': False,
                    'shopping_list_count': 0,
                    'shopping_list_limit': 1,
                    'shopping_list_can_create': False,
                },
                'features': {key: False for key in [
                    'recipe_matching', 'advanced_matching', 'meal_planning',
                    'nutrition_tracking', 'analytics', 'advanced_analytics',
                    'export', 'api_access', 'ocr_receipts', 'voice_input',
                    'priority_support'
                ]},
                'is_active': False,
                'is_trialing': False,
                'is_expired': False,
                'expires_soon': False,
                'trial_ends_soon': False,
            }

    def handle_expired_subscription(self, request):
        """Handle expired subscriptions and show appropriate messages."""
        if not hasattr(request.user, 'subscription'):
            return
        
        subscription = request.user.subscription
        path = request.path
        
        # Skip checks for exempt paths
        if any(path.startswith(exempt_path) for exempt_path in self.exempt_paths):
            return
        
        # Check if subscription is expired
        if not subscription.is_active and path in self.premium_paths:
            messages.warning(
                request,
                "Your subscription has expired. Some features may be limited. "
                "Please update your payment method to restore full access."
            )
            return
        
        # Check if trial is ending soon
        if (subscription.is_trialing and 
            request.subscription.get('trial_ends_soon') and 
            not hasattr(request, '_trial_warning_shown')):
            
            days_left = (subscription.trial_end - timezone.now()).days
            messages.info(
                request,
                f"Your trial ends in {days_left} day{'s' if days_left != 1 else ''}. "
                f"Upgrade now to continue using premium features."
            )
            # Prevent showing this message multiple times in the same session
            request._trial_warning_shown = True
        
        # Check if subscription is expiring soon
        if (subscription.is_active and 
            request.subscription.get('expires_soon') and
            not hasattr(request, '_expiry_warning_shown')):
            
            days_left = (subscription.current_period_end - timezone.now()).days
            messages.warning(
                request,
                f"Your subscription expires in {days_left} day{'s' if days_left != 1 else ''}. "
                f"Make sure your payment method is up to date."
            )
            request._expiry_warning_shown = True

    def should_show_upgrade_prompt(self, request, feature=None):
        """
        Determine if an upgrade prompt should be shown for the current user/request.
        
        Args:
            request: The current request
            feature: Optional specific feature being accessed
            
        Returns:
            dict with prompt information or None
        """
        if not request.user.is_authenticated:
            return None
        
        plan = request.user.get_subscription_plan()
        if not plan or plan.tier == 'free':
            usage = request.subscription['usage']
            
            # Show prompt if user is near limits
            prompts = []
            
            if usage['inventory_count'] >= usage['inventory_limit'] * 0.8:
                prompts.append({
                    'type': 'inventory',
                    'message': f"You're using {usage['inventory_count']} of {usage['inventory_limit']} inventory slots.",
                    'cta': "Upgrade for unlimited inventory tracking"
                })
            
            if usage['recipe_searches_today'] >= usage['recipe_search_limit'] * 0.8:
                prompts.append({
                    'type': 'recipe_search',
                    'message': f"You've used {usage['recipe_searches_today']} of {usage['recipe_search_limit']} daily recipe searches.",
                    'cta': "Upgrade for unlimited recipe searches"
                })
            
            if feature and not request.subscription['features'].get(feature):
                feature_names = {
                    'recipe_matching': 'Recipe Matching',
                    'analytics': 'Analytics Dashboard',
                    'export': 'Data Export',
                }
                prompts.append({
                    'type': 'feature',
                    'message': f"{feature_names.get(feature, feature)} is a premium feature.",
                    'cta': f"Upgrade to access {feature_names.get(feature, feature)}"
                })
            
            return prompts if prompts else None
        
        return None


class UsageTrackingMiddleware:
    """
    Lightweight middleware to track usage patterns for analytics.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Track usage after successful requests
        if (request.user.is_authenticated and 
            response.status_code == 200 and 
            request.method == 'GET'):
            self.track_page_view(request)
        
        return response

    def track_page_view(self, request):
        """Track page views for analytics."""
        path = request.path
        user = request.user
        
        # Track specific feature usage
        feature_paths = {
            '/recipes/discover/': 'recipe_discovery',
            '/analytics/': 'analytics_dashboard',
            '/inventory/export/': 'data_export',
            '/recipes/create/': 'recipe_creation',
            '/shopping/lists/': 'shopping_lists',
        }
        
        if path in feature_paths:
            # This could be expanded to store in database or send to analytics service
            feature = feature_paths[path]
            # For now, we'll just pass - could implement actual tracking here
            pass