"""
Insights views with subscription-aware analytics dashboard.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from subscriptions.decorators import feature_required
from inventory.models import InventoryItem
from recipes.models import Recipe, UserRecipeInteraction
from shopping.models import ShoppingList, ShoppingListItem


@login_required
@feature_required('analytics')
def analytics_dashboard(request):
    """
    Basic analytics dashboard for premium users.
    """
    user = request.user
    household = user.household
    
    if not household:
        messages.info(request, "Please create or join a household first.")
        return redirect("accounts:household_create")
    
    # Get date range (default to last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Inventory Analytics
    inventory_stats = {
        'total_items': InventoryItem.objects.filter(household=household, is_consumed=False).count(),
        'items_added_month': InventoryItem.objects.filter(
            household=household,
            created_at__gte=start_date
        ).count(),
        'expired_items': InventoryItem.objects.filter(
            household=household,
            expiration_date__lt=timezone.now().date()
        ).count(),
        'expiring_soon': InventoryItem.objects.filter(
            household=household,
            expiration_date__gte=timezone.now().date(),
            expiration_date__lte=timezone.now().date() + timedelta(days=7)
        ).count(),
    }
    
    # Category breakdown
    category_breakdown = InventoryItem.objects.filter(
        household=household, 
        is_consumed=False
    ).values(
        'product__category__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Recipe Analytics
    recipe_stats = {
        'recipes_viewed': UserRecipeInteraction.objects.filter(
            user=user,
            created_at__gte=start_date,
            interaction_type='view'
        ).count(),
        'recipes_cooked': UserRecipeInteraction.objects.filter(
            user=user,
            created_at__gte=start_date,
            interaction_type='cook'
        ).count(),
        'favorite_recipes': UserRecipeInteraction.objects.filter(
            user=user,
            interaction_type='favorite'
        ).count(),
    }
    
    # Shopping Analytics
    shopping_stats = {
        'active_lists': ShoppingList.objects.filter(
            household=household,
            status='active'
        ).count(),
        'completed_lists_month': ShoppingList.objects.filter(
            household=household,
            status='completed',
            updated_at__gte=start_date
        ).count(),
        'total_items_bought': ShoppingListItem.objects.filter(
            shopping_list__household=household,
            is_purchased=True,
            updated_at__gte=start_date
        ).count(),
    }
    
    context = {
        'inventory_stats': inventory_stats,
        'category_breakdown': category_breakdown,
        'recipe_stats': recipe_stats,
        'shopping_stats': shopping_stats,
        'date_range': {
            'start': start_date.date(),
            'end': end_date.date()
        },
        'is_premium': user.has_premium_features(),
        'is_pro': user.has_pro_features(),
    }
    
    return render(request, 'insights/dashboard.html', context)


@login_required
@feature_required('advanced_analytics')
def advanced_analytics(request):
    """
    Advanced analytics dashboard for pro users.
    """
    user = request.user
    household = user.household
    
    if not household:
        messages.info(request, "Please create or join a household first.")
        return redirect("accounts:household_create")
    
    # Advanced metrics for pro users
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)  # 3 months of data
    
    # Monthly trends
    monthly_inventory_growth = []
    monthly_recipe_activity = []
    
    for i in range(3):  # Last 3 months
        month_start = end_date - timedelta(days=30 * (i + 1))
        month_end = end_date - timedelta(days=30 * i)
        
        inventory_count = InventoryItem.objects.filter(
            household=household,
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        
        recipe_interactions = UserRecipeInteraction.objects.filter(
            user=user,
            created_at__gte=month_start,
            created_at__lt=month_end
        ).count()
        
        monthly_inventory_growth.append({
            'month': month_start.strftime('%B'),
            'count': inventory_count
        })
        
        monthly_recipe_activity.append({
            'month': month_start.strftime('%B'),
            'count': recipe_interactions
        })
    
    # Cost savings estimation
    expired_items_value = InventoryItem.objects.filter(
        household=household,
        expiration_date__lt=timezone.now().date(),
        expiration_date__gte=start_date.date()
    ).count() * 3.50  # Rough estimate of $3.50 per expired item
    
    # Waste reduction insights
    consumption_rate = InventoryItem.objects.filter(
        household=household,
        is_consumed=True,
        consumed_date__gte=start_date.date()
    ).count()
    
    context = {
        'monthly_inventory_growth': reversed(monthly_inventory_growth),
        'monthly_recipe_activity': reversed(monthly_recipe_activity),
        'cost_insights': {
            'estimated_waste_cost': expired_items_value,
            'items_consumed': consumption_rate,
            'waste_percentage': (expired_items_value / (consumption_rate * 3.50 * 100)) if consumption_rate > 0 else 0
        },
        'date_range': {
            'start': start_date.date(),
            'end': end_date.date()
        },
    }
    
    return render(request, 'insights/advanced_dashboard.html', context)


@login_required  
@feature_required('export')
def export_data(request):
    """
    Data export functionality for pro users.
    """
    user = request.user
    household = user.household
    
    if not household:
        messages.info(request, "Please create or join a household first.")
        return redirect("accounts:household_create")
    
    # This would implement various export formats
    # For now, just show the export options
    context = {
        'available_exports': [
            {'name': 'Inventory Export', 'format': 'CSV', 'description': 'All inventory items with details'},
            {'name': 'Recipe Collection', 'format': 'JSON', 'description': 'Your saved and created recipes'},
            {'name': 'Shopping History', 'format': 'CSV', 'description': 'All shopping list history'},
            {'name': 'Usage Analytics', 'format': 'PDF', 'description': 'Comprehensive usage report'},
        ]
    }
    
    return render(request, 'insights/export.html', context)