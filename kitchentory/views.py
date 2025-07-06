from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from datetime import date, timedelta

from inventory.models import InventoryItem
from recipes.models import Recipe


@login_required
def dashboard(request):
    """
    Main dashboard view showing inventory stats and recent activities.
    """
    # Check if user has a household
    if not hasattr(request.user, 'household') or not request.user.household:
        messages.info(request, _('Please create or join a household first.'))
        return redirect('accounts:household_create')
    
    household = request.user.household
    
    # Get inventory statistics
    items = InventoryItem.objects.filter(
        household=household,
        is_consumed=False
    )
    
    stats = {
        'total_items': items.count(),
        'expiring_soon': items.filter(
            expiration_date__lte=date.today() + timedelta(days=7),
            expiration_date__gte=date.today()
        ).count(),
        'expired': items.filter(
            expiration_date__lt=date.today()
        ).count(),
        'categories': items.values('product__category__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
    }
    
    # Get items expiring soon
    expiring_items = items.filter(
        expiration_date__lte=date.today() + timedelta(days=7)
    ).select_related(
        'product', 'product__category', 'location'
    ).order_by('expiration_date')[:10]
    
    # Get recent recipes (public recipes or user's own)
    recent_recipes = Recipe.objects.filter(
        is_public=True
    ).select_related('category').prefetch_related('tags').order_by('-created_at')[:6]
    
    context = {
        'stats': stats,
        'expiring_items': expiring_items,
        'recent_recipes': recent_recipes,
        'household': household,
    }
    
    return render(request, 'home.html', context)