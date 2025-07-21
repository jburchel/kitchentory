from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.db.models import Q
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class GracefulDegradationHandler:
    """
    Handles graceful degradation of features when subscriptions expire
    or users downgrade their plans.
    """
    
    @classmethod
    def handle_subscription_expiry(cls, user):
        """
        Handle actions when a user's subscription expires.
        
        Args:
            user: User instance whose subscription has expired
        """
        from .models import SubscriptionPlan
        
        try:
            # Move user to free plan
            free_plan = SubscriptionPlan.objects.get(tier='free')
            user.current_plan = free_plan
            user.subscription_status = 'expired'
            user.save(update_fields=['current_plan', 'subscription_status'])
            
            # Apply free plan limits
            cls.apply_plan_limits(user, free_plan)
            
            logger.info(f"Applied graceful degradation for expired subscription: {user.email}")
            
        except Exception as e:
            logger.error(f"Error handling subscription expiry for {user.email}: {str(e)}")
    
    @classmethod
    def apply_plan_limits(cls, user, plan):
        """
        Apply plan limits to user's data when downgrading.
        
        Args:
            user: User instance
            plan: SubscriptionPlan instance with new limits
        """
        from .models import InventoryUsage, ShoppingListUsage
        from inventory.models import InventoryItem
        from shopping.models import ShoppingList
        
        # Handle inventory limits
        if plan.max_inventory_items:
            inventory_usage, _ = InventoryUsage.objects.get_or_create(user=user)
            current_count = InventoryItem.objects.filter(user=user).count()
            
            if current_count > plan.max_inventory_items:
                # Hide excess items (oldest first) rather than deleting them
                excess_items = InventoryItem.objects.filter(
                    user=user
                ).order_by('created_at')[plan.max_inventory_items:]
                
                # Mark items as hidden/archived
                for item in excess_items:
                    item.is_active = False
                    item.save()
                
                # Update usage count
                inventory_usage.item_count = plan.max_inventory_items
                inventory_usage.save()
                
                logger.info(
                    f"Archived {len(excess_items)} inventory items for user {user.email} "
                    f"due to plan limit ({plan.max_inventory_items})"
                )
        
        # Handle shopping list limits
        if plan.max_shopping_lists:
            shopping_usage, _ = ShoppingListUsage.objects.get_or_create(user=user)
            current_lists = ShoppingList.objects.filter(
                Q(user=user) | Q(household=user.household)
            ).count()
            
            if current_lists > plan.max_shopping_lists:
                # Archive excess shopping lists (oldest first)
                excess_lists = ShoppingList.objects.filter(
                    Q(user=user) | Q(household=user.household)
                ).order_by('created_at')[plan.max_shopping_lists:]
                
                for shopping_list in excess_lists:
                    shopping_list.is_active = False
                    shopping_list.save()
                
                shopping_usage.list_count = plan.max_shopping_lists
                shopping_usage.save()
                
                logger.info(
                    f"Archived {len(excess_lists)} shopping lists for user {user.email} "
                    f"due to plan limit ({plan.max_shopping_lists})"
                )
    
    @classmethod
    def restore_archived_data(cls, user, new_plan):
        """
        Restore previously archived data when upgrading to a higher plan.
        
        Args:
            user: User instance
            new_plan: SubscriptionPlan instance with higher limits
        """
        from inventory.models import InventoryItem
        from shopping.models import ShoppingList
        
        restored_items = []
        
        # Restore inventory items if plan allows
        if not new_plan.max_inventory_items or new_plan.max_inventory_items > 50:
            # Restore previously archived inventory items
            archived_items = InventoryItem.objects.filter(
                user=user,
                is_active=False
            )
            
            if new_plan.max_inventory_items:
                # Restore up to the limit
                items_to_restore = archived_items[:new_plan.max_inventory_items - 50]
            else:
                # Unlimited plan - restore all
                items_to_restore = archived_items
            
            for item in items_to_restore:
                item.is_active = True
                item.save()
                restored_items.append(f"inventory:{item.id}")
            
            if items_to_restore:
                logger.info(
                    f"Restored {len(items_to_restore)} inventory items for user {user.email} "
                    f"after plan upgrade"
                )
        
        # Restore shopping lists if plan allows
        if not new_plan.max_shopping_lists or new_plan.max_shopping_lists > 1:
            archived_lists = ShoppingList.objects.filter(
                Q(user=user) | Q(household=user.household),
                is_active=False
            )
            
            if new_plan.max_shopping_lists:
                lists_to_restore = archived_lists[:new_plan.max_shopping_lists - 1]
            else:
                lists_to_restore = archived_lists
            
            for shopping_list in lists_to_restore:
                shopping_list.is_active = True
                shopping_list.save()
                restored_items.append(f"shopping_list:{shopping_list.id}")
            
            if lists_to_restore:
                logger.info(
                    f"Restored {len(lists_to_restore)} shopping lists for user {user.email} "
                    f"after plan upgrade"
                )
        
        return restored_items


class SubscriptionValidationUtils:
    """
    Utilities for validating subscription status and permissions.
    """
    
    @classmethod
    def can_access_feature(cls, user, feature_name):
        """
        Check if user can access a specific feature.
        
        Args:
            user: User instance
            feature_name: Name of the feature to check
            
        Returns:
            bool: True if user can access the feature
        """
        if not user.is_authenticated:
            return False
        
        plan = user.get_subscription_plan()
        if not plan:
            return False
        
        # Check if subscription is active
        if hasattr(user, 'subscription') and not user.subscription.is_active:
            return False
        
        return getattr(plan, f'has_{feature_name}', False)
    
    @classmethod
    def check_usage_limit(cls, user, limit_type):
        """
        Check if user is within usage limits for a specific resource.
        
        Args:
            user: User instance
            limit_type: Type of limit to check ('inventory', 'recipe_search', 'shopping_list')
            
        Returns:
            dict with limit information
        """
        from .models import InventoryUsage, RecipeSearchUsage, ShoppingListUsage
        
        plan = user.get_subscription_plan()
        if not plan:
            return {'can_proceed': False, 'reason': 'No subscription plan'}
        
        if limit_type == 'inventory':
            usage, _ = InventoryUsage.objects.get_or_create(user=user)
            return {
                'can_proceed': usage.can_add_item(),
                'current': usage.item_count,
                'limit': plan.max_inventory_items,
                'unlimited': plan.max_inventory_items is None
            }
        
        elif limit_type == 'recipe_search':
            current_count = RecipeSearchUsage.get_today_count(user)
            can_search = RecipeSearchUsage.can_search(user)
            return {
                'can_proceed': can_search,
                'current': current_count,
                'limit': plan.max_recipes_per_day,
                'unlimited': plan.max_recipes_per_day is None,
                'resets': 'daily'
            }
        
        elif limit_type == 'shopping_list':
            usage, _ = ShoppingListUsage.objects.get_or_create(user=user)
            return {
                'can_proceed': usage.can_create_list(),
                'current': usage.list_count,
                'limit': plan.max_shopping_lists,
                'unlimited': plan.max_shopping_lists is None
            }
        
        return {'can_proceed': False, 'reason': 'Unknown limit type'}
    
    @classmethod
    def get_feature_restrictions(cls, user):
        """
        Get a complete list of feature restrictions for a user.
        
        Args:
            user: User instance
            
        Returns:
            dict with feature availability and restrictions
        """
        if not user.is_authenticated:
            return cls._get_anonymous_restrictions()
        
        plan = user.get_subscription_plan()
        if not plan:
            return cls._get_free_plan_restrictions()
        
        # Get usage limits
        inventory_limit = cls.check_usage_limit(user, 'inventory')
        recipe_limit = cls.check_usage_limit(user, 'recipe_search')
        shopping_limit = cls.check_usage_limit(user, 'shopping_list')
        
        # Get feature availability
        features = {}
        feature_list = [
            'recipe_matching', 'advanced_matching', 'meal_planning',
            'nutrition_tracking', 'analytics', 'advanced_analytics',
            'export', 'api_access', 'ocr_receipts', 'voice_input'
        ]
        
        for feature in feature_list:
            features[feature] = getattr(plan, f'has_{feature}', False)
        
        return {
            'plan': {
                'tier': plan.tier,
                'name': plan.name,
                'is_active': getattr(user.subscription, 'is_active', True) if hasattr(user, 'subscription') else True
            },
            'limits': {
                'inventory': inventory_limit,
                'recipe_search': recipe_limit,
                'shopping_list': shopping_limit,
            },
            'features': features,
            'can_upgrade': plan.tier in ['free', 'premium'],
            'can_downgrade': plan.tier in ['premium', 'pro']
        }
    
    @classmethod
    def _get_anonymous_restrictions(cls):
        """Get restrictions for anonymous users."""
        return {
            'plan': {'tier': 'anonymous', 'name': 'Not logged in', 'is_active': False},
            'limits': {
                'inventory': {'can_proceed': False, 'current': 0, 'limit': 0},
                'recipe_search': {'can_proceed': False, 'current': 0, 'limit': 0},
                'shopping_list': {'can_proceed': False, 'current': 0, 'limit': 0},
            },
            'features': {feature: False for feature in [
                'recipe_matching', 'advanced_matching', 'meal_planning',
                'nutrition_tracking', 'analytics', 'advanced_analytics',
                'export', 'api_access', 'ocr_receipts', 'voice_input'
            ]},
            'can_upgrade': True,
            'can_downgrade': False
        }
    
    @classmethod
    def _get_free_plan_restrictions(cls):
        """Get restrictions for free plan users."""
        return {
            'plan': {'tier': 'free', 'name': 'Free Plan', 'is_active': True},
            'limits': {
                'inventory': {'can_proceed': True, 'current': 0, 'limit': 50},
                'recipe_search': {'can_proceed': True, 'current': 0, 'limit': 5},
                'shopping_list': {'can_proceed': True, 'current': 0, 'limit': 1},
            },
            'features': {feature: False for feature in [
                'recipe_matching', 'advanced_matching', 'meal_planning',
                'nutrition_tracking', 'analytics', 'advanced_analytics',
                'export', 'api_access', 'ocr_receipts', 'voice_input'
            ]},
            'can_upgrade': True,
            'can_downgrade': False
        }


class SubscriptionNotificationHelper:
    """
    Helper class for generating subscription-related notifications and messages.
    """
    
    @classmethod
    def get_upgrade_message(cls, current_tier, feature_requested=None):
        """
        Get an appropriate upgrade message for the user's current situation.
        
        Args:
            current_tier: Current subscription tier
            feature_requested: Optional specific feature that triggered the message
            
        Returns:
            dict with message details
        """
        messages_map = {
            'free_to_premium': {
                'title': 'Upgrade to Premium',
                'message': 'Unlock unlimited inventory, recipe matching, and more premium features.',
                'cta': 'Upgrade to Premium - $4.99/month',
                'urgency': 'medium'
            },
            'free_to_pro': {
                'title': 'Upgrade to Pro',
                'message': 'Get all Premium features plus AI meal planning, nutrition tracking, and advanced analytics.',
                'cta': 'Upgrade to Pro - $9.99/month',
                'urgency': 'low'
            },
            'premium_to_pro': {
                'title': 'Upgrade to Pro',
                'message': 'Add nutrition tracking, advanced analytics, and AI-powered meal planning.',
                'cta': 'Upgrade to Pro - $9.99/month',
                'urgency': 'low'
            }
        }
        
        # Feature-specific messages
        if feature_requested:
            feature_messages = {
                'recipe_matching': {
                    'title': 'Recipe Matching Available in Premium',
                    'message': 'Find recipes based on your inventory items with Premium.',
                    'cta': 'Upgrade to Premium',
                    'urgency': 'high'
                },
                'nutrition_tracking': {
                    'title': 'Nutrition Tracking Available in Pro',
                    'message': 'Track nutritional goals and dietary requirements with Pro.',
                    'cta': 'Upgrade to Pro',
                    'urgency': 'medium'
                },
                'analytics': {
                    'title': 'Analytics Dashboard Available in Premium',
                    'message': 'View detailed usage patterns and insights with Premium.',
                    'cta': 'Upgrade to Premium',
                    'urgency': 'medium'
                }
            }
            
            if feature_requested in feature_messages:
                return feature_messages[feature_requested]
        
        # Default tier-based messages
        if current_tier == 'free':
            return messages_map['free_to_premium']
        elif current_tier == 'premium':
            return messages_map['premium_to_pro']
        
        return messages_map['free_to_premium']  # fallback
    
    @classmethod
    def get_limit_warning_message(cls, limit_type, current, limit):
        """
        Get a warning message when approaching usage limits.
        
        Args:
            limit_type: Type of limit ('inventory', 'recipe_search', etc.)
            current: Current usage count
            limit: Maximum allowed
            
        Returns:
            dict with warning message
        """
        percentage_used = (current / limit) * 100 if limit > 0 else 0
        
        if percentage_used >= 90:
            urgency = 'high'
        elif percentage_used >= 75:
            urgency = 'medium'
        else:
            urgency = 'low'
        
        limit_messages = {
            'inventory': {
                'title': f'Inventory Limit: {current}/{limit}',
                'message': f"You're using {current} of {limit} inventory slots.",
                'cta': 'Upgrade for unlimited inventory',
                'urgency': urgency
            },
            'recipe_search': {
                'title': f'Daily Searches: {current}/{limit}',
                'message': f"You've used {current} of {limit} daily recipe searches.",
                'cta': 'Upgrade for unlimited searches',
                'urgency': urgency
            },
            'shopping_list': {
                'title': f'Shopping Lists: {current}/{limit}',
                'message': f"You're using {current} of {limit} shopping lists.",
                'cta': 'Upgrade for unlimited lists',
                'urgency': urgency
            }
        }
        
        return limit_messages.get(limit_type, {
            'title': 'Usage Limit',
            'message': f"You're using {current} of {limit} allowed items.",
            'cta': 'Upgrade your plan',
            'urgency': urgency
        })