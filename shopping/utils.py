"""
Utility functions for shopping list functionality.
"""

from django.db.models import Q, F, Count, Avg
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
from typing import List, Dict, Tuple, Optional

from inventory.models import InventoryItem, Product
from recipes.models import Recipe, RecipeIngredient
from .models import ShoppingList, ShoppingListItem, RecurringShoppingItem


def detect_depleted_items(user, threshold_days: int = 7, min_threshold: float = 1.0) -> List[Dict]:
    """
    Detect inventory items that are running low and should be added to shopping list.
    
    Args:
        user: User to check inventory for
        threshold_days: Number of days to look ahead for depletion
        min_threshold: Minimum quantity threshold for considering an item depleted
    
    Returns:
        List of dictionaries containing depleted item information
    """
    depleted_items = []
    
    # Get user's inventory items
    inventory_items = InventoryItem.objects.filter(
        user=user,
        quantity__gt=0
    ).select_related('product', 'category')
    
    for item in inventory_items:
        depletion_info = _calculate_depletion_timeline(user, item, threshold_days)
        
        # Check if item will be depleted within threshold
        if (depletion_info['days_until_empty'] <= threshold_days or 
            item.quantity <= min_threshold):
            
            depleted_items.append({
                'inventory_item': item,
                'product': item.product,
                'current_quantity': float(item.quantity),
                'estimated_days_remaining': depletion_info['days_until_empty'],
                'daily_usage_rate': depletion_info['daily_usage'],
                'suggested_quantity': _calculate_suggested_quantity(item, depletion_info),
                'priority': _calculate_priority(item, depletion_info),
                'reason': _get_depletion_reason(item, depletion_info, min_threshold)
            })
    
    # Sort by priority (urgent first)
    depleted_items.sort(key=lambda x: (
        0 if x['priority'] == 'urgent' else
        1 if x['priority'] == 'high' else
        2 if x['priority'] == 'medium' else 3
    ))
    
    return depleted_items


def _calculate_depletion_timeline(user, inventory_item, days_ahead: int) -> Dict:
    """
    Calculate how quickly an inventory item is being depleted.
    """
    # Look at usage patterns from cooking sessions and manual adjustments
    from recipes.models import CookingSession
    
    # Get recent cooking sessions that used this item
    recent_date = timezone.now() - timedelta(days=30)
    cooking_sessions = CookingSession.objects.filter(
        user=user,
        status='completed',
        completed_at__gte=recent_date,
        recipe__ingredients__product=inventory_item.product
    ).distinct()
    
    total_usage = 0
    usage_days = 0
    
    for session in cooking_sessions:
        # Calculate how much of this item was used in the session
        recipe_ingredients = session.recipe.ingredients.filter(
            product=inventory_item.product
        )
        
        for ingredient in recipe_ingredients:
            if ingredient.quantity:
                serving_multiplier = (session.servings_planned / session.recipe.servings 
                                    if session.recipe.servings > 0 else 1.0)
                usage_amount = float(ingredient.quantity) * serving_multiplier
                total_usage += usage_amount
                usage_days = max(usage_days, 
                    (timezone.now().date() - session.completed_at.date()).days)
    
    # Calculate daily usage rate
    if usage_days > 0 and total_usage > 0:
        daily_usage = total_usage / usage_days
    else:
        # Fallback: estimate based on typical consumption patterns
        daily_usage = _estimate_daily_usage(inventory_item)
    
    # Calculate days until empty
    if daily_usage > 0:
        days_until_empty = inventory_item.quantity / daily_usage
    else:
        days_until_empty = float('inf')
    
    return {
        'daily_usage': daily_usage,
        'days_until_empty': min(days_until_empty, 999),  # Cap at 999 days
        'total_recent_usage': total_usage,
        'usage_period_days': usage_days
    }


def _estimate_daily_usage(inventory_item) -> float:
    """
    Estimate daily usage for an item based on category and typical patterns.
    """
    category_usage_rates = {
        'dairy': 0.15,      # Milk, yogurt, etc. - used frequently
        'vegetables': 0.20,  # Fresh vegetables - spoil quickly
        'fruits': 0.18,     # Fresh fruits - spoil quickly
        'meat': 0.12,       # Meat products - planned meals
        'pantry': 0.05,     # Dry goods - last longer
        'spices': 0.02,     # Spices - small amounts
        'condiments': 0.03, # Condiments - occasional use
        'beverages': 0.25,  # Drinks - consumed daily
        'snacks': 0.30,     # Snacks - consumed quickly
    }
    
    category_name = inventory_item.category.name.lower() if inventory_item.category else 'pantry'
    base_rate = category_usage_rates.get(category_name, 0.10)
    
    # Adjust based on quantity (larger quantities used more slowly per day)
    if inventory_item.quantity > 10:
        base_rate *= 0.8
    elif inventory_item.quantity < 2:
        base_rate *= 1.5
    
    return base_rate


def _calculate_suggested_quantity(inventory_item, depletion_info: Dict) -> float:
    """
    Calculate suggested quantity to purchase based on usage patterns.
    """
    daily_usage = depletion_info['daily_usage']
    
    if daily_usage <= 0:
        # Default suggestion based on typical purchase amounts
        return _get_typical_purchase_amount(inventory_item)
    
    # Suggest enough for 2 weeks of usage
    suggested_days = 14
    suggested_quantity = daily_usage * suggested_days
    
    # Round to reasonable purchase increments
    if suggested_quantity < 1:
        return round(suggested_quantity, 2)
    elif suggested_quantity < 10:
        return round(suggested_quantity, 1)
    else:
        return round(suggested_quantity)


def _get_typical_purchase_amount(inventory_item) -> float:
    """
    Get typical purchase amount for an item based on its category.
    """
    category_amounts = {
        'dairy': 2.0,       # 2 units (cartons, packages)
        'vegetables': 3.0,  # 3 units/pounds
        'fruits': 2.0,      # 2 pounds/packages
        'meat': 2.0,        # 2 pounds
        'pantry': 1.0,      # 1 package/box
        'spices': 1.0,      # 1 container
        'condiments': 1.0,  # 1 bottle/jar
        'beverages': 4.0,   # 4 bottles/cans
        'snacks': 2.0,      # 2 packages
    }
    
    category_name = inventory_item.category.name.lower() if inventory_item.category else 'pantry'
    return category_amounts.get(category_name, 1.0)


def _calculate_priority(inventory_item, depletion_info: Dict) -> str:
    """
    Calculate priority level for restocking an item.
    """
    days_remaining = depletion_info['days_until_empty']
    current_quantity = inventory_item.quantity
    
    # Urgent: Will run out within 2 days or already very low
    if days_remaining <= 2 or current_quantity <= 0.5:
        return 'urgent'
    
    # High: Will run out within a week
    elif days_remaining <= 7:
        return 'high'
    
    # Medium: Will run out within 2 weeks
    elif days_remaining <= 14:
        return 'medium'
    
    # Low: Will run out later
    else:
        return 'low'


def _get_depletion_reason(inventory_item, depletion_info: Dict, min_threshold: float) -> str:
    """
    Get human-readable reason for why item should be restocked.
    """
    days_remaining = depletion_info['days_until_empty']
    current_quantity = inventory_item.quantity
    
    if current_quantity <= min_threshold:
        return f"Quantity is low ({current_quantity:.1f} remaining)"
    elif days_remaining <= 1:
        return "Will run out today"
    elif days_remaining <= 2:
        return f"Will run out in {days_remaining:.0f} days"
    elif days_remaining <= 7:
        return f"Will run out in {days_remaining:.0f} days"
    else:
        return f"Will run out in {days_remaining:.0f} days"


def create_depletion_shopping_list(user, depleted_items: List[Dict], 
                                 list_name: str = None) -> ShoppingList:
    """
    Create a shopping list from depleted inventory items.
    
    Args:
        user: User to create list for
        depleted_items: List of depleted items from detect_depleted_items()
        list_name: Custom name for the shopping list
    
    Returns:
        Created ShoppingList instance
    """
    if not list_name:
        list_name = f"Low Inventory - {timezone.now().strftime('%B %d')}"
    
    # Create the shopping list
    shopping_list = ShoppingList.objects.create(
        name=list_name,
        description="Automatically generated from low inventory items",
        created_by=user,
        generation_source='depletion',
        auto_update=True
    )
    
    # Add items to the shopping list
    for item_data in depleted_items:
        inventory_item = item_data['inventory_item']
        suggested_quantity = item_data['suggested_quantity']
        priority = item_data['priority']
        
        # Check if item already exists in an active shopping list
        existing_item = ShoppingListItem.objects.filter(
            shopping_list__created_by=user,
            shopping_list__status__in=['active', 'shopping'],
            product=inventory_item.product,
            is_purchased=False
        ).first()
        
        if not existing_item:
            ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                product=inventory_item.product,
                name=inventory_item.product.name if inventory_item.product else inventory_item.name,
                quantity=Decimal(str(suggested_quantity)),
                unit=inventory_item.unit,
                category=inventory_item.category.name if inventory_item.category else '',
                priority=priority,
                added_by=user,
                notes=f"Low inventory: {item_data['reason']}"
            )
    
    # Calculate estimated total
    shopping_list.calculate_estimated_total()
    
    return shopping_list


def get_recurring_items_due(user) -> List[RecurringShoppingItem]:
    """
    Get recurring shopping items that are due to be added to a shopping list.
    
    Args:
        user: User to check recurring items for
    
    Returns:
        List of RecurringShoppingItem instances that are due
    """
    recurring_items = RecurringShoppingItem.objects.filter(
        user=user,
        is_active=True
    )
    
    due_items = []
    for item in recurring_items:
        if item.is_due():
            due_items.append(item)
    
    return due_items


def add_recurring_items_to_list(shopping_list: ShoppingList, 
                               recurring_items: List[RecurringShoppingItem]) -> int:
    """
    Add recurring items to a shopping list.
    
    Args:
        shopping_list: ShoppingList to add items to
        recurring_items: List of RecurringShoppingItem instances to add
    
    Returns:
        Number of items added
    """
    added_count = 0
    
    for recurring_item in recurring_items:
        # Check if item already exists in the list
        existing_item = shopping_list.items.filter(
            product=recurring_item.product,
            is_purchased=False
        ).first()
        
        if not existing_item:
            ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                product=recurring_item.product,
                name=recurring_item.name,
                quantity=recurring_item.quantity,
                unit=recurring_item.unit,
                is_recurring=True,
                added_by=shopping_list.created_by,
                notes="Recurring item"
            )
            
            # Update last_added timestamp
            recurring_item.last_added = timezone.now()
            recurring_item.save()
            
            added_count += 1
    
    return added_count


def auto_update_shopping_lists(user) -> Dict[str, int]:
    """
    Automatically update user's shopping lists with depleted and recurring items.
    
    Args:
        user: User to update lists for
    
    Returns:
        Dictionary with update statistics
    """
    stats = {
        'depleted_items_found': 0,
        'recurring_items_due': 0,
        'lists_updated': 0,
        'new_lists_created': 0
    }
    
    # Find depleted items
    depleted_items = detect_depleted_items(user)
    stats['depleted_items_found'] = len(depleted_items)
    
    # Find recurring items due
    recurring_items = get_recurring_items_due(user)
    stats['recurring_items_due'] = len(recurring_items)
    
    # Get or create an active shopping list
    active_list = ShoppingList.objects.filter(
        created_by=user,
        status='active',
        auto_update=True
    ).first()
    
    if not active_list and (depleted_items or recurring_items):
        # Create new shopping list
        active_list = ShoppingList.objects.create(
            name=f"Shopping List - {timezone.now().strftime('%B %d')}",
            description="Auto-updated with low inventory and recurring items",
            created_by=user,
            generation_source='depletion',
            auto_update=True
        )
        stats['new_lists_created'] = 1
    
    if active_list:
        # Add depleted items
        if depleted_items:
            for item_data in depleted_items:
                inventory_item = item_data['inventory_item']
                
                # Check if item already exists
                existing_item = active_list.items.filter(
                    product=inventory_item.product,
                    is_purchased=False
                ).first()
                
                if not existing_item:
                    ShoppingListItem.objects.create(
                        shopping_list=active_list,
                        product=inventory_item.product,
                        name=inventory_item.product.name if inventory_item.product else inventory_item.name,
                        quantity=Decimal(str(item_data['suggested_quantity'])),
                        unit=inventory_item.unit,
                        category=inventory_item.category.name if inventory_item.category else '',
                        priority=item_data['priority'],
                        added_by=user,
                        notes=f"Auto-added: {item_data['reason']}"
                    )
        
        # Add recurring items
        if recurring_items:
            add_recurring_items_to_list(active_list, recurring_items)
        
        # Update list totals
        active_list.calculate_estimated_total()
        stats['lists_updated'] = 1
    
    return stats


def create_recipe_shopping_list(user, recipes: List[Recipe], servings_map: Dict[int, int] = None,
                               list_name: str = None) -> ShoppingList:
    """
    Create a shopping list from one or more recipes.
    
    Args:
        user: User to create list for
        recipes: List of Recipe instances to include
        servings_map: Dictionary mapping recipe IDs to desired servings (optional)
        list_name: Custom name for the shopping list
    
    Returns:
        Created ShoppingList instance
    """
    if not list_name:
        if len(recipes) == 1:
            list_name = f"Recipe: {recipes[0].title}"
        else:
            list_name = f"Meal Plan - {timezone.now().strftime('%B %d')}"
    
    # Create the shopping list
    shopping_list = ShoppingList.objects.create(
        name=list_name,
        description=f"Generated from {len(recipes)} recipe(s)",
        created_by=user,
        generation_source='recipe'
    )
    
    # Track ingredient consolidation
    ingredient_map = {}  # product_id -> consolidated quantity
    
    for recipe in recipes:
        # Determine serving multiplier
        desired_servings = servings_map.get(recipe.id, recipe.servings) if servings_map else recipe.servings
        serving_multiplier = desired_servings / recipe.servings if recipe.servings > 0 else 1.0
        
        # Process recipe ingredients
        for recipe_ingredient in recipe.ingredients.all():
            if recipe_ingredient.product:
                product_id = recipe_ingredient.product.id
                
                # Calculate adjusted quantity
                base_quantity = float(recipe_ingredient.quantity) if recipe_ingredient.quantity else 0
                adjusted_quantity = base_quantity * serving_multiplier
                
                if product_id in ingredient_map:
                    # Consolidate with existing ingredient
                    existing_data = ingredient_map[product_id]
                    existing_data['total_quantity'] += adjusted_quantity
                    existing_data['recipes'].append({
                        'recipe': recipe,
                        'original_quantity': base_quantity,
                        'adjusted_quantity': adjusted_quantity,
                        'serving_multiplier': serving_multiplier
                    })
                else:
                    # Add new ingredient
                    ingredient_map[product_id] = {
                        'product': recipe_ingredient.product,
                        'name': recipe_ingredient.name,
                        'total_quantity': adjusted_quantity,
                        'unit': recipe_ingredient.unit,
                        'category': recipe_ingredient.category,
                        'is_optional': recipe_ingredient.is_optional,
                        'recipes': [{
                            'recipe': recipe,
                            'original_quantity': base_quantity,
                            'adjusted_quantity': adjusted_quantity,
                            'serving_multiplier': serving_multiplier
                        }]
                    }
    
    # Create shopping list items from consolidated ingredients
    for product_id, ingredient_data in ingredient_map.items():
        # Check current inventory
        current_inventory = _get_current_inventory_amount(user, ingredient_data['product'])
        needed_quantity = max(0, ingredient_data['total_quantity'] - current_inventory)
        
        if needed_quantity > 0:
            # Create detailed notes about recipe usage
            recipe_notes = []
            for recipe_data in ingredient_data['recipes']:
                recipe_notes.append(
                    f"{recipe_data['recipe'].title}: {recipe_data['adjusted_quantity']:.1f} {ingredient_data['unit']}"
                )
            
            ShoppingListItem.objects.create(
                shopping_list=shopping_list,
                product=ingredient_data['product'],
                name=ingredient_data['name'],
                quantity=Decimal(str(needed_quantity)),
                unit=ingredient_data['unit'],
                category=ingredient_data['category'],
                priority='high' if not ingredient_data['is_optional'] else 'medium',
                added_by=user,
                notes=f"For recipes: {'; '.join(recipe_notes[:3])}" + 
                      (f" and {len(recipe_notes)-3} more" if len(recipe_notes) > 3 else "")
            )
    
    # Calculate estimated total
    shopping_list.calculate_estimated_total()
    
    return shopping_list


def _get_current_inventory_amount(user, product) -> float:
    """
    Get current inventory amount for a product.
    """
    try:
        inventory_item = InventoryItem.objects.get(user=user, product=product)
        return float(inventory_item.quantity)
    except InventoryItem.DoesNotExist:
        return 0.0


def analyze_recipe_coverage(user, recipes: List[Recipe], servings_map: Dict[int, int] = None) -> Dict:
    """
    Analyze how well current inventory covers recipe requirements.
    
    Args:
        user: User to check inventory for
        recipes: List of Recipe instances to analyze
        servings_map: Dictionary mapping recipe IDs to desired servings
    
    Returns:
        Dictionary with coverage analysis
    """
    analysis = {
        'total_ingredients': 0,
        'available_ingredients': 0,
        'missing_ingredients': 0,
        'partially_available': 0,
        'coverage_percentage': 0,
        'missing_items': [],
        'available_items': [],
        'recipe_analyses': []
    }
    
    for recipe in recipes:
        recipe_analysis = _analyze_single_recipe_coverage(user, recipe, servings_map)
        analysis['recipe_analyses'].append(recipe_analysis)
        
        # Aggregate totals
        analysis['total_ingredients'] += recipe_analysis['total_ingredients']
        analysis['available_ingredients'] += recipe_analysis['available_ingredients']
        analysis['missing_ingredients'] += recipe_analysis['missing_ingredients']
        analysis['partially_available'] += recipe_analysis['partially_available']
        
        # Collect missing items (avoid duplicates)
        for item in recipe_analysis['missing_items']:
            if not any(existing['product_id'] == item['product_id'] 
                      for existing in analysis['missing_items']):
                analysis['missing_items'].append(item)
    
    # Calculate overall coverage
    if analysis['total_ingredients'] > 0:
        analysis['coverage_percentage'] = (
            analysis['available_ingredients'] / analysis['total_ingredients']
        ) * 100
    
    return analysis


def _analyze_single_recipe_coverage(user, recipe: Recipe, servings_map: Dict[int, int] = None) -> Dict:
    """
    Analyze inventory coverage for a single recipe.
    """
    # Determine serving multiplier
    desired_servings = servings_map.get(recipe.id, recipe.servings) if servings_map else recipe.servings
    serving_multiplier = desired_servings / recipe.servings if recipe.servings > 0 else 1.0
    
    analysis = {
        'recipe': recipe,
        'serving_multiplier': serving_multiplier,
        'total_ingredients': 0,
        'available_ingredients': 0,
        'missing_ingredients': 0,
        'partially_available': 0,
        'missing_items': [],
        'available_items': [],
        'cookable': True
    }
    
    for recipe_ingredient in recipe.ingredients.all():
        analysis['total_ingredients'] += 1
        
        if recipe_ingredient.product:
            # Check inventory
            current_amount = _get_current_inventory_amount(user, recipe_ingredient.product)
            needed_amount = (float(recipe_ingredient.quantity) * serving_multiplier 
                           if recipe_ingredient.quantity else 0)
            
            if current_amount >= needed_amount:
                # Sufficient quantity available
                analysis['available_ingredients'] += 1
                analysis['available_items'].append({
                    'name': recipe_ingredient.name,
                    'needed': needed_amount,
                    'available': current_amount,
                    'sufficient': True
                })
            elif current_amount > 0:
                # Partially available
                analysis['partially_available'] += 1
                analysis['missing_items'].append({
                    'product_id': recipe_ingredient.product.id,
                    'name': recipe_ingredient.name,
                    'needed': needed_amount,
                    'available': current_amount,
                    'missing': needed_amount - current_amount,
                    'unit': recipe_ingredient.unit,
                    'is_optional': recipe_ingredient.is_optional
                })
                
                if not recipe_ingredient.is_optional:
                    analysis['cookable'] = False
            else:
                # Completely missing
                analysis['missing_ingredients'] += 1
                analysis['missing_items'].append({
                    'product_id': recipe_ingredient.product.id,
                    'name': recipe_ingredient.name,
                    'needed': needed_amount,
                    'available': 0,
                    'missing': needed_amount,
                    'unit': recipe_ingredient.unit,
                    'is_optional': recipe_ingredient.is_optional
                })
                
                if not recipe_ingredient.is_optional:
                    analysis['cookable'] = False
        else:
            # No product linked - assume missing
            analysis['missing_ingredients'] += 1
            analysis['missing_items'].append({
                'product_id': None,
                'name': recipe_ingredient.name,
                'needed': float(recipe_ingredient.quantity) * serving_multiplier if recipe_ingredient.quantity else 0,
                'available': 0,
                'missing': float(recipe_ingredient.quantity) * serving_multiplier if recipe_ingredient.quantity else 0,
                'unit': recipe_ingredient.unit,
                'is_optional': recipe_ingredient.is_optional
            })
            
            if not recipe_ingredient.is_optional:
                analysis['cookable'] = False
    
    return analysis


def smart_suggest_additions(user, shopping_list: ShoppingList, limit: int = 10) -> List[Dict]:
    """
    Suggest smart additions to a shopping list based on user patterns and complementary items.
    
    Args:
        user: User to generate suggestions for
        shopping_list: Shopping list to suggest additions for
        limit: Maximum number of suggestions to return
    
    Returns:
        List of suggestion dictionaries
    """
    suggestions = []
    
    # Get items currently in the shopping list
    current_items = set(
        item.product.id for item in shopping_list.items.all() 
        if item.product and not item.is_purchased
    )
    
    # Analyze user's cooking patterns
    frequently_used_items = _get_frequently_used_items(user, exclude_products=current_items)
    complementary_items = _get_complementary_items(user, current_items)
    seasonal_suggestions = _get_seasonal_suggestions(exclude_products=current_items)
    
    # Combine and score suggestions
    all_suggestions = []
    
    # Add frequently used items
    for item in frequently_used_items[:5]:
        all_suggestions.append({
            'product': item['product'],
            'reason': f"You use this frequently ({item['usage_count']} times recently)",
            'score': item['usage_count'] * 2,
            'category': 'frequent'
        })
    
    # Add complementary items
    for item in complementary_items[:5]:
        all_suggestions.append({
            'product': item['product'],
            'reason': f"Often used with {item['trigger_item']}",
            'score': item['confidence'] * 10,
            'category': 'complementary'
        })
    
    # Add seasonal suggestions
    for item in seasonal_suggestions[:3]:
        all_suggestions.append({
            'product': item['product'],
            'reason': f"Seasonal suggestion: {item['reason']}",
            'score': 5,
            'category': 'seasonal'
        })
    
    # Sort by score and return top suggestions
    all_suggestions.sort(key=lambda x: x['score'], reverse=True)
    return all_suggestions[:limit]


def _get_frequently_used_items(user, exclude_products: set = None, days: int = 60) -> List[Dict]:
    """
    Get items frequently used by the user in recent cooking sessions.
    """
    from recipes.models import CookingSession
    
    if exclude_products is None:
        exclude_products = set()
    
    recent_date = timezone.now() - timedelta(days=days)
    
    # Count product usage in completed cooking sessions
    usage_counts = {}
    
    completed_sessions = CookingSession.objects.filter(
        user=user,
        status='completed',
        completed_at__gte=recent_date
    ).select_related('recipe')
    
    for session in completed_sessions:
        for ingredient in session.recipe.ingredients.all():
            if (ingredient.product and 
                ingredient.product.id not in exclude_products):
                
                product_id = ingredient.product.id
                if product_id in usage_counts:
                    usage_counts[product_id]['usage_count'] += 1
                else:
                    usage_counts[product_id] = {
                        'product': ingredient.product,
                        'usage_count': 1
                    }
    
    # Sort by usage count
    frequent_items = list(usage_counts.values())
    frequent_items.sort(key=lambda x: x['usage_count'], reverse=True)
    
    return frequent_items


def _get_complementary_items(user, current_product_ids: set) -> List[Dict]:
    """
    Get items that are frequently used together with items in the current shopping list.
    """
    from recipes.models import CookingSession
    
    complementary_items = {}
    
    # Find recipes that contain current shopping list items
    recipes_with_current_items = Recipe.objects.filter(
        ingredients__product__id__in=current_product_ids
    ).distinct()
    
    # Find other ingredients in those recipes
    for recipe in recipes_with_current_items:
        trigger_items = []
        other_items = []
        
        for ingredient in recipe.ingredients.all():
            if ingredient.product:
                if ingredient.product.id in current_product_ids:
                    trigger_items.append(ingredient.product.name)
                else:
                    other_items.append(ingredient.product)
        
        # Add complementary relationships
        for other_product in other_items:
            product_id = other_product.id
            if product_id in complementary_items:
                complementary_items[product_id]['confidence'] += 1
            else:
                complementary_items[product_id] = {
                    'product': other_product,
                    'confidence': 1,
                    'trigger_item': ', '.join(trigger_items[:2])
                }
    
    # Sort by confidence
    complementary_list = list(complementary_items.values())
    complementary_list.sort(key=lambda x: x['confidence'], reverse=True)
    
    return complementary_list


def _get_seasonal_suggestions(exclude_products: set = None) -> List[Dict]:
    """
    Get seasonal product suggestions based on current time of year.
    """
    if exclude_products is None:
        exclude_products = set()
    
    current_month = timezone.now().month
    
    # Seasonal suggestions by month (simplified)
    seasonal_items = {
        # Winter (Dec, Jan, Feb)
        12: ['root vegetables', 'citrus fruits', 'hearty grains'],
        1: ['root vegetables', 'citrus fruits', 'hearty grains'],
        2: ['root vegetables', 'citrus fruits', 'hearty grains'],
        
        # Spring (Mar, Apr, May)
        3: ['spring vegetables', 'fresh herbs', 'asparagus'],
        4: ['spring vegetables', 'fresh herbs', 'asparagus'],
        5: ['spring vegetables', 'fresh herbs', 'strawberries'],
        
        # Summer (Jun, Jul, Aug)
        6: ['berries', 'stone fruits', 'summer squash'],
        7: ['berries', 'stone fruits', 'tomatoes'],
        8: ['berries', 'stone fruits', 'corn'],
        
        # Fall (Sep, Oct, Nov)
        9: ['apples', 'pumpkins', 'winter squash'],
        10: ['apples', 'pumpkins', 'winter squash'],
        11: ['cranberries', 'sweet potatoes', 'brussels sprouts'],
    }
    
    suggestions = []
    seasonal_keywords = seasonal_items.get(current_month, [])
    
    # This is a simplified implementation
    # In a real app, you'd query your Product database for items matching seasonal keywords
    for keyword in seasonal_keywords:
        suggestions.append({
            'product': None,  # Would be actual Product instance
            'reason': f"{keyword} are in season",
            'keyword': keyword
        })
    
    return suggestions


def consolidate_shopping_list_quantities(shopping_list: ShoppingList) -> Dict[str, int]:
    """
    Consolidate duplicate items in a shopping list and optimize quantities.
    
    Args:
        shopping_list: ShoppingList to consolidate
    
    Returns:
        Dictionary with consolidation statistics
    """
    from django.db.models import Sum
    from collections import defaultdict
    
    stats = {
        'items_before': shopping_list.items.count(),
        'items_after': 0,
        'items_consolidated': 0,
        'duplicates_removed': 0
    }
    
    # Group items by product and unit
    item_groups = defaultdict(list)
    
    for item in shopping_list.items.filter(is_purchased=False):
        # Create grouping key: product_id + unit (normalized)
        product_key = item.product.id if item.product else f"name_{item.name.lower()}"
        unit_key = _normalize_unit(item.unit)
        group_key = f"{product_key}_{unit_key}"
        
        item_groups[group_key].append(item)
    
    # Process each group
    for group_key, items in item_groups.items():
        if len(items) > 1:
            # Multiple items with same product/unit - consolidate
            primary_item = items[0]  # Keep the first item
            total_quantity = Decimal('0')
            all_notes = []
            priorities = []
            source_recipes = []
            
            for item in items:
                total_quantity += item.quantity
                if item.notes:
                    all_notes.append(item.notes)
                priorities.append(item.priority)
                if item.source_recipe:
                    source_recipes.append(item.source_recipe.title)
            
            # Update primary item with consolidated data
            primary_item.quantity = total_quantity
            primary_item.notes = '; '.join(set(all_notes))
            primary_item.priority = _consolidate_priorities(priorities)
            
            if source_recipes:
                recipe_list = ', '.join(set(source_recipes))
                if primary_item.notes:
                    primary_item.notes += f" | Recipes: {recipe_list}"
                else:
                    primary_item.notes = f"Recipes: {recipe_list}"
            
            primary_item.save()
            
            # Delete duplicate items
            for item in items[1:]:
                item.delete()
                stats['duplicates_removed'] += 1
            
            stats['items_consolidated'] += 1
    
    # Apply quantity optimization
    _optimize_purchase_quantities(shopping_list)
    
    stats['items_after'] = shopping_list.items.filter(is_purchased=False).count()
    
    # Update shopping list totals
    shopping_list.calculate_estimated_total()
    
    return stats


def _normalize_unit(unit: str) -> str:
    """
    Normalize unit names for consolidation.
    """
    if not unit:
        return "each"
    
    unit = unit.lower().strip()
    
    # Unit normalization mappings
    unit_mappings = {
        # Weight
        'lb': 'pound',
        'lbs': 'pound',
        'pounds': 'pound',
        'oz': 'ounce',
        'ounces': 'ounce',
        'g': 'gram',
        'grams': 'gram',
        'kg': 'kilogram',
        'kilograms': 'kilogram',
        
        # Volume
        'fl oz': 'fluid_ounce',
        'fluid ounces': 'fluid_ounce',
        'cup': 'cup',
        'cups': 'cup',
        'pint': 'pint',
        'pints': 'pint',
        'quart': 'quart',
        'quarts': 'quart',
        'gallon': 'gallon',
        'gallons': 'gallon',
        'ml': 'milliliter',
        'milliliters': 'milliliter',
        'l': 'liter',
        'liter': 'liter',
        'liters': 'liter',
        
        # Count
        'piece': 'each',
        'pieces': 'each',
        'item': 'each',
        'items': 'each',
        'unit': 'each',
        'units': 'each',
        '': 'each',
    }
    
    return unit_mappings.get(unit, unit)


def _consolidate_priorities(priorities: List[str]) -> str:
    """
    Determine the highest priority from a list of priorities.
    """
    priority_order = ['urgent', 'high', 'medium', 'low']
    
    for priority in priority_order:
        if priority in priorities:
            return priority
    
    return 'medium'  # Default


def _optimize_purchase_quantities(shopping_list: ShoppingList):
    """
    Optimize purchase quantities based on typical package sizes and bulk discounts.
    """
    # Package size mappings for common items
    package_sizes = {
        # Dairy
        'milk': {'unit': 'gallon', 'sizes': [0.5, 1.0]},
        'yogurt': {'unit': 'cup', 'sizes': [6, 32]},
        'cheese': {'unit': 'ounce', 'sizes': [8, 16, 32]},
        
        # Produce
        'banana': {'unit': 'each', 'sizes': [1, 6, 12]},
        'apple': {'unit': 'each', 'sizes': [1, 3, 6, 12]},
        'orange': {'unit': 'each', 'sizes': [1, 4, 8]},
        
        # Pantry
        'rice': {'unit': 'pound', 'sizes': [1, 2, 5, 10]},
        'flour': {'unit': 'pound', 'sizes': [2, 5, 10]},
        'sugar': {'unit': 'pound', 'sizes': [1, 2, 4, 10]},
        
        # Meat
        'chicken breast': {'unit': 'pound', 'sizes': [1, 2, 3, 5]},
        'ground beef': {'unit': 'pound', 'sizes': [1, 2, 3]},
    }
    
    for item in shopping_list.items.filter(is_purchased=False):
        if not item.product:
            continue
            
        product_name = item.product.name.lower()
        
        # Check if we have package size data for this product
        for product_key, size_data in package_sizes.items():
            if product_key in product_name:
                normalized_unit = _normalize_unit(item.unit)
                if normalized_unit == _normalize_unit(size_data['unit']):
                    # Find the best package size
                    needed_quantity = float(item.quantity)
                    best_size = _find_optimal_package_size(needed_quantity, size_data['sizes'])
                    
                    if best_size > needed_quantity:
                        # Update quantity to package size
                        original_quantity = item.quantity
                        item.quantity = Decimal(str(best_size))
                        
                        # Add note about optimization
                        optimization_note = f"Optimized from {original_quantity} to {best_size} (package size)"
                        if item.notes:
                            item.notes += f" | {optimization_note}"
                        else:
                            item.notes = optimization_note
                        
                        item.save()
                break


def _find_optimal_package_size(needed_quantity: float, available_sizes: List[float]) -> float:
    """
    Find the optimal package size that minimizes waste while meeting the need.
    """
    # Sort sizes to find the smallest size that meets or exceeds the need
    available_sizes = sorted(available_sizes)
    
    for size in available_sizes:
        if size >= needed_quantity:
            return size
    
    # If no single package is large enough, return the largest size
    # (user will need to buy multiple packages)
    return available_sizes[-1] if available_sizes else needed_quantity


def calculate_shopping_list_metrics(shopping_list: ShoppingList) -> Dict:
    """
    Calculate comprehensive metrics for a shopping list.
    
    Args:
        shopping_list: ShoppingList to analyze
    
    Returns:
        Dictionary with various metrics
    """
    items = shopping_list.items.all()
    active_items = items.filter(is_purchased=False)
    completed_items = items.filter(is_purchased=True)
    
    # Basic counts
    metrics = {
        'total_items': items.count(),
        'active_items': active_items.count(),
        'completed_items': completed_items.count(),
        'completion_percentage': 0,
        
        # Priority breakdown
        'urgent_items': active_items.filter(priority='urgent').count(),
        'high_items': active_items.filter(priority='high').count(),
        'medium_items': active_items.filter(priority='medium').count(),
        'low_items': active_items.filter(priority='low').count(),
        
        # Category breakdown
        'categories': {},
        
        # Financial metrics
        'estimated_total': float(shopping_list.estimated_total),
        'actual_total': float(shopping_list.actual_total) if shopping_list.actual_total else 0,
        'estimated_remaining': 0,
        'budget_variance': 0,
        
        # Time estimates
        'estimated_shopping_time': 0,
        'items_per_store_section': {},
        
        # Generation source breakdown
        'recipe_items': active_items.filter(source_recipe__isnull=False).count(),
        'recurring_items': active_items.filter(is_recurring=True).count(),
        'manual_items': active_items.filter(source_recipe__isnull=True, is_recurring=False).count(),
    }
    
    # Calculate completion percentage
    if metrics['total_items'] > 0:
        metrics['completion_percentage'] = (
            metrics['completed_items'] / metrics['total_items']
        ) * 100
    
    # Category breakdown
    from django.db.models import Count
    category_counts = active_items.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for cat in category_counts:
        if cat['category']:
            metrics['categories'][cat['category']] = cat['count']
    
    # Financial calculations
    estimated_remaining = sum(
        float(item.estimated_total) for item in active_items
        if item.estimated_price
    )
    metrics['estimated_remaining'] = estimated_remaining
    
    if shopping_list.actual_total and shopping_list.estimated_total:
        metrics['budget_variance'] = float(shopping_list.actual_total - shopping_list.estimated_total)
    
    # Time estimates (rough calculation)
    # Assume 2 minutes per item + 5 minutes per unique store section
    metrics['estimated_shopping_time'] = (
        metrics['active_items'] * 2 +  # 2 min per item
        len(set(item.store_section for item in active_items if item.store_section)) * 5  # 5 min per section
    )
    
    # Store section breakdown
    section_counts = active_items.values('store_section').annotate(
        count=Count('id')
    ).order_by('-count')
    
    for section in section_counts:
        if section['store_section']:
            metrics['items_per_store_section'][section['store_section']] = section['count']
    
    return metrics


def generate_shopping_efficiency_report(user, days: int = 30) -> Dict:
    """
    Generate a shopping efficiency report for a user.
    
    Args:
        user: User to generate report for
        days: Number of days to look back
    
    Returns:
        Dictionary with efficiency metrics
    """
    from django.utils import timezone
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Get shopping lists in the time period
    completed_lists = ShoppingList.objects.filter(
        created_by=user,
        status='completed',
        shopping_completed_at__gte=cutoff_date
    )
    
    all_lists = ShoppingList.objects.filter(
        created_by=user,
        created_at__gte=cutoff_date
    )
    
    # Calculate metrics
    report = {
        'period_days': days,
        'total_lists_created': all_lists.count(),
        'lists_completed': completed_lists.count(),
        'lists_abandoned': all_lists.filter(status='abandoned').count(),
        'completion_rate': 0,
        
        'total_items_planned': 0,
        'total_items_purchased': 0,
        'purchase_completion_rate': 0,
        
        'total_estimated_cost': 0,
        'total_actual_cost': 0,
        'budget_accuracy': 0,
        'average_budget_variance': 0,
        
        'average_shopping_time': 0,
        'most_common_categories': {},
        'most_frequent_items': {},
        
        'efficiency_trends': []
    }
    
    if all_lists.count() > 0:
        report['completion_rate'] = (completed_lists.count() / all_lists.count()) * 100
    
    # Aggregate item and cost data
    total_items_planned = 0
    total_items_purchased = 0
    total_estimated = Decimal('0')
    total_actual = Decimal('0')
    shopping_times = []
    
    for shopping_list in all_lists:
        list_metrics = calculate_shopping_list_metrics(shopping_list)
        total_items_planned += list_metrics['total_items']
        total_items_purchased += list_metrics['completed_items']
        
        if shopping_list.estimated_total:
            total_estimated += shopping_list.estimated_total
        if shopping_list.actual_total:
            total_actual += shopping_list.actual_total
        
        # Calculate shopping time if available
        if (shopping_list.shopping_started_at and 
            shopping_list.shopping_completed_at):
            shopping_time = (
                shopping_list.shopping_completed_at - 
                shopping_list.shopping_started_at
            ).total_seconds() / 60  # Convert to minutes
            shopping_times.append(shopping_time)
    
    report['total_items_planned'] = total_items_planned
    report['total_items_purchased'] = total_items_purchased
    
    if total_items_planned > 0:
        report['purchase_completion_rate'] = (
            total_items_purchased / total_items_planned
        ) * 100
    
    report['total_estimated_cost'] = float(total_estimated)
    report['total_actual_cost'] = float(total_actual)
    
    if total_estimated > 0:
        report['budget_accuracy'] = (total_actual / total_estimated) * 100
        report['average_budget_variance'] = float(total_actual - total_estimated) / completed_lists.count() if completed_lists.count() > 0 else 0
    
    if shopping_times:
        report['average_shopping_time'] = sum(shopping_times) / len(shopping_times)
    
    return report


def optimize_shopping_route(shopping_list: ShoppingList, store_layout: List[str] = None) -> Dict:
    """
    Optimize the shopping route based on store layout.
    
    Args:
        shopping_list: ShoppingList to optimize
        store_layout: Optional custom store layout (list of section names in order)
    
    Returns:
        Dictionary with optimization results
    """
    if not shopping_list.store and not store_layout:
        return {
            'success': False,
            'message': 'No store or layout information available',
            'optimized_items': []
        }
    
    # Use store layout or provided layout
    if store_layout:
        sections = store_layout
    elif shopping_list.store:
        sections = shopping_list.store.default_sections
    else:
        sections = []
    
    # Get items that need to be organized
    items = shopping_list.items.filter(is_purchased=False)
    
    # Create section mapping
    section_order = {section: idx for idx, section in enumerate(sections)}
    
    # Organize items by section
    optimized_items = []
    unassigned_items = []
    
    for item in items:
        if item.store_section and item.store_section in section_order:
            # Item already has a section assignment
            item.section_order = section_order[item.store_section]
            optimized_items.append({
                'item': item,
                'section': item.store_section,
                'order': item.section_order,
                'assigned': True
            })
        else:
            # Try to assign section based on category or product type
            assigned_section = _assign_item_to_section(item, sections)
            if assigned_section:
                item.store_section = assigned_section
                item.section_order = section_order[assigned_section]
                optimized_items.append({
                    'item': item,
                    'section': assigned_section,
                    'order': item.section_order,
                    'assigned': False  # Newly assigned
                })
            else:
                # Put unassigned items at the end
                item.section_order = 999
                unassigned_items.append({
                    'item': item,
                    'section': 'Other',
                    'order': 999,
                    'assigned': False
                })
        
        item.save()
    
    # Sort by section order
    optimized_items.sort(key=lambda x: x['order'])
    
    # Mark list as optimized
    shopping_list.is_optimized = True
    shopping_list.save()
    
    return {
        'success': True,
        'message': f'Optimized {len(optimized_items)} items across {len(set(item["section"] for item in optimized_items))} sections',
        'optimized_items': optimized_items,
        'unassigned_items': unassigned_items,
        'sections_used': list(set(item['section'] for item in optimized_items)),
        'estimated_time_saved': len(optimized_items) * 0.5  # Rough estimate: 30 seconds per item
    }


def _assign_item_to_section(item, sections: List[str]) -> str:
    """
    Assign an item to a store section based on its category or name.
    """
    # Category to section mapping
    category_mapping = {
        'fruits': 'Produce',
        'vegetables': 'Produce',
        'produce': 'Produce',
        'dairy': 'Dairy',
        'milk': 'Dairy',
        'cheese': 'Dairy',
        'yogurt': 'Dairy',
        'meat': 'Meat & Seafood',
        'poultry': 'Meat & Seafood',
        'seafood': 'Meat & Seafood',
        'fish': 'Meat & Seafood',
        'deli': 'Deli',
        'bakery': 'Bakery',
        'bread': 'Bakery',
        'frozen': 'Frozen',
        'beverages': 'Beverages',
        'drinks': 'Beverages',
        'soda': 'Beverages',
        'juice': 'Beverages',
        'snacks': 'Snacks',
        'chips': 'Snacks',
        'crackers': 'Snacks',
        'pantry': 'Pantry',
        'canned': 'Pantry',
        'spices': 'Pantry',
        'condiments': 'Pantry',
        'household': 'Household',
        'cleaning': 'Household',
        'health': 'Health & Beauty',
        'beauty': 'Health & Beauty',
        'personal care': 'Health & Beauty',
    }
    
    # Try to match by category first
    if item.category:
        category_lower = item.category.lower()
        for category_key, section in category_mapping.items():
            if category_key in category_lower and section in sections:
                return section
    
    # Try to match by product name
    if item.product and item.product.name:
        product_name = item.product.name.lower()
        for category_key, section in category_mapping.items():
            if category_key in product_name and section in sections:
                return section
    
    # Try to match by item name
    item_name = item.name.lower()
    for category_key, section in category_mapping.items():
        if category_key in item_name and section in sections:
            return section
    
    # Default fallback
    return 'Other' if 'Other' in sections else None


def bulk_update_shopping_lists() -> Dict:
    """
    Bulk update all active shopping lists with depletion detection and optimization.
    
    Returns:
        Dictionary with update statistics
    """
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    total_stats = {
        'users_processed': 0,
        'lists_updated': 0,
        'items_added': 0,
        'lists_optimized': 0,
        'errors': []
    }
    
    # Get all users with active shopping lists
    users_with_lists = User.objects.filter(
        created_shopping_lists__status='active'
    ).distinct()
    
    for user in users_with_lists:
        try:
            # Update with depleted items
            stats = auto_update_shopping_lists(user)
            total_stats['users_processed'] += 1
            total_stats['lists_updated'] += stats['lists_updated']
            
            # Optimize active lists
            active_lists = ShoppingList.objects.filter(
                created_by=user,
                status='active',
                is_optimized=False
            )
            
            for shopping_list in active_lists:
                if shopping_list.store:
                    optimization_result = optimize_shopping_route(shopping_list)
                    if optimization_result['success']:
                        total_stats['lists_optimized'] += 1
                
        except Exception as e:
            total_stats['errors'].append(f"User {user.username}: {str(e)}")
    
    return total_stats