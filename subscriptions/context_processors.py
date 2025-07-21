from django.utils import timezone
from .models import SubscriptionPlan


def subscription_context(request):
    """
    Context processor that adds subscription information to all templates.
    """
    context = {
        'subscription_plans': None,
        'current_plan': None,
        'subscription_status': None,
        'usage_limits': None,
        'feature_flags': None,
        'upgrade_prompts': None,
    }
    
    if request.user.is_authenticated:
        # Get subscription context from middleware (if available)
        if hasattr(request, 'subscription'):
            subscription_data = request.subscription
            
            context.update({
                'current_plan': subscription_data['plan'],
                'subscription_tier': subscription_data['tier'],
                'is_premium_user': subscription_data['is_premium'],
                'is_pro_user': subscription_data['is_pro'],
                'usage_limits': subscription_data['usage'],
                'feature_flags': subscription_data['features'],
                'subscription_status': {
                    'is_active': subscription_data.get('is_active', True),
                    'is_trialing': subscription_data.get('is_trialing', False),
                    'is_expired': subscription_data.get('is_expired', False),
                    'expires_soon': subscription_data.get('expires_soon', False),
                    'trial_ends_soon': subscription_data.get('trial_ends_soon', False),
                    'current_period_end': subscription_data.get('current_period_end'),
                    'trial_end': subscription_data.get('trial_end'),
                }
            })
        else:
            # Fallback if middleware isn't running
            plan = request.user.get_subscription_plan()
            context.update({
                'current_plan': plan,
                'subscription_tier': plan.tier if plan else 'free',
                'is_premium_user': request.user.has_premium_features(),
                'is_pro_user': request.user.has_pro_features(),
            })
    
    # Always provide subscription plans for comparison pages
    context['subscription_plans'] = SubscriptionPlan.objects.filter(
        is_active=True
    ).order_by('monthly_price')
    
    return context


def upgrade_prompts(request):
    """
    Context processor that determines when to show upgrade prompts.
    """
    if not request.user.is_authenticated:
        return {}
    
    prompts = []
    
    # Check if middleware has determined upgrade prompts should be shown
    if hasattr(request, 'subscription'):
        subscription_data = request.subscription
        
        # Near inventory limit
        usage = subscription_data.get('usage', {})
        if (usage.get('inventory_count', 0) >= usage.get('inventory_limit', 50) * 0.9 and
            subscription_data.get('tier') == 'free'):
            prompts.append({
                'type': 'inventory_limit',
                'title': 'Running low on inventory space',
                'message': f"You're using {usage['inventory_count']} of {usage['inventory_limit']} slots.",
                'cta': 'Upgrade for unlimited inventory',
                'urgency': 'high' if usage['inventory_count'] >= usage['inventory_limit'] else 'medium'
            })
        
        # Near recipe search limit
        if (usage.get('recipe_searches_today', 0) >= usage.get('recipe_search_limit', 5) * 0.8 and
            subscription_data.get('tier') == 'free'):
            prompts.append({
                'type': 'recipe_search_limit',
                'title': 'Daily recipe search limit',
                'message': f"You've used {usage['recipe_searches_today']} of {usage['recipe_search_limit']} searches today.",
                'cta': 'Upgrade for unlimited searches',
                'urgency': 'high' if usage['recipe_searches_today'] >= usage['recipe_search_limit'] else 'medium'
            })
        
        # Trial ending soon
        if subscription_data.get('trial_ends_soon'):
            days_left = 0
            if subscription_data.get('trial_end'):
                days_left = (subscription_data['trial_end'] - timezone.now()).days
            
            prompts.append({
                'type': 'trial_ending',
                'title': 'Trial ending soon',
                'message': f"Your trial ends in {days_left} day{'s' if days_left != 1 else ''}.",
                'cta': 'Choose your plan',
                'urgency': 'high'
            })
        
        # Subscription expiring soon
        if subscription_data.get('expires_soon'):
            days_left = 0
            if subscription_data.get('current_period_end'):
                days_left = (subscription_data['current_period_end'] - timezone.now()).days
            
            prompts.append({
                'type': 'subscription_expiring',
                'title': 'Subscription expiring',
                'message': f"Your subscription expires in {days_left} day{'s' if days_left != 1 else ''}.",
                'cta': 'Update payment method',
                'urgency': 'high'
            })
    
    return {
        'upgrade_prompts': prompts,
        'has_upgrade_prompts': len(prompts) > 0,
        'urgent_prompts': [p for p in prompts if p.get('urgency') == 'high'],
    }


def subscription_stats(request):
    """
    Context processor that adds subscription statistics for admin users.
    """
    if not (request.user.is_authenticated and request.user.is_staff):
        return {}
    
    # Only calculate stats for admin pages or when explicitly requested
    if not (request.path.startswith('/admin/') or 'subscription_stats' in request.GET):
        return {}
    
    try:
        from django.db.models import Count
        from accounts.models import User
        
        # Calculate subscription statistics
        stats = {
            'total_users': User.objects.count(),
            'free_users': User.objects.filter(
                current_plan__tier='free'
            ).count(),
            'premium_users': User.objects.filter(
                current_plan__tier='premium'
            ).count(),
            'pro_users': User.objects.filter(
                current_plan__tier='pro'
            ).count(),
        }
        
        # Calculate conversion rates
        if stats['total_users'] > 0:
            stats.update({
                'free_percentage': round((stats['free_users'] / stats['total_users']) * 100, 1),
                'premium_percentage': round((stats['premium_users'] / stats['total_users']) * 100, 1),
                'pro_percentage': round((stats['pro_users'] / stats['total_users']) * 100, 1),
                'paid_conversion_rate': round(
                    ((stats['premium_users'] + stats['pro_users']) / stats['total_users']) * 100, 1
                ),
            })
        
        return {'subscription_stats': stats}
    
    except Exception:
        # If there's any error calculating stats, return empty dict
        return {}


def feature_availability(request):
    """
    Context processor that provides feature availability information for templates.
    """
    if not request.user.is_authenticated:
        return {
            'available_features': [],
            'unavailable_features': [],
            'feature_descriptions': {},
        }
    
    plan = request.user.get_subscription_plan()
    if not plan:
        return {
            'available_features': [],
            'unavailable_features': [],
            'feature_descriptions': {},
        }
    
    # Define all features with descriptions
    all_features = {
        'recipe_matching': {
            'name': 'Recipe Matching',
            'description': 'Find recipes based on your inventory',
            'icon': 'search',
        },
        'advanced_matching': {
            'name': 'Advanced Recipe Matching',
            'description': 'Smart substitutions and "almost there" recipes',
            'icon': 'sparkles',
        },
        'meal_planning': {
            'name': 'Meal Planning',
            'description': 'Plan your weekly meals',
            'icon': 'calendar',
        },
        'nutrition_tracking': {
            'name': 'Nutrition Tracking',
            'description': 'Track nutritional information and goals',
            'icon': 'heart',
        },
        'analytics': {
            'name': 'Analytics Dashboard',
            'description': 'View usage patterns and insights',
            'icon': 'chart-bar',
        },
        'advanced_analytics': {
            'name': 'Advanced Analytics',
            'description': 'Detailed reports and trend analysis',
            'icon': 'chart-pie',
        },
        'export': {
            'name': 'Data Export',
            'description': 'Export your data in various formats',
            'icon': 'download',
        },
        'api_access': {
            'name': 'API Access',
            'description': 'Programmatic access to your data',
            'icon': 'code',
        },
        'ocr_receipts': {
            'name': 'Receipt Scanning',
            'description': 'Scan receipts to add items automatically',
            'icon': 'camera',
        },
        'voice_input': {
            'name': 'Voice Input',
            'description': 'Add items and search using voice commands',
            'icon': 'microphone',
        },
    }
    
    # Determine which features are available
    available_features = []
    unavailable_features = []
    
    for feature_key, feature_info in all_features.items():
        if getattr(plan, f'has_{feature_key}', False):
            available_features.append(feature_key)
        else:
            unavailable_features.append(feature_key)
    
    return {
        'available_features': available_features,
        'unavailable_features': unavailable_features,
        'feature_descriptions': all_features,
    }