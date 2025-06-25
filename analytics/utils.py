"""
Utility functions for analytics and consumption pattern tracking.
"""

from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
import statistics
from calendar import monthrange

from .models import ConsumptionPattern, UsageEvent, BudgetTracking, ReorderPrediction
from inventory.models import InventoryItem
from recipes.models import CookingSession


def track_usage_event(user, product, quantity_used: Decimal, unit: str, 
                     event_type: str, inventory_item=None, recipe=None, 
                     cooking_session=None, notes: str = "") -> UsageEvent:
    """
    Track a usage event for analytics.
    
    Args:
        user: User who used the item
        product: Product that was used
        quantity_used: Amount used
        unit: Unit of measurement
        event_type: Type of usage event
        inventory_item: Related inventory item (optional)
        recipe: Related recipe (optional)
        cooking_session: Related cooking session (optional)
        notes: Additional notes
    
    Returns:
        Created UsageEvent instance
    """
    usage_event = UsageEvent.objects.create(
        user=user,
        product=product,
        inventory_item=inventory_item,
        event_type=event_type,
        quantity_used=quantity_used,
        unit=unit,
        recipe=recipe,
        cooking_session=cooking_session,
        notes=notes
    )
    
    # Update consumption pattern asynchronously
    _update_consumption_pattern(user, product)
    
    return usage_event


def _update_consumption_pattern(user, product):
    """
    Update consumption pattern for a product based on recent usage events.
    """
    # Get or create consumption pattern
    pattern, created = ConsumptionPattern.objects.get_or_create(
        user=user,
        product=product,
        defaults={
            'consumption_unit': product.default_unit,
        }
    )
    
    # Get usage events from the last 90 days
    ninety_days_ago = timezone.now() - timedelta(days=90)
    usage_events = UsageEvent.objects.filter(
        user=user,
        product=product,
        event_date__gte=ninety_days_ago,
        event_type__in=['cooking_session', 'manual_consumption', 'recipe_cooking']
    ).order_by('event_date')
    
    if not usage_events.exists():
        return pattern
    
    # Calculate consumption patterns
    pattern.data_points_count = usage_events.count()
    
    # Calculate weekly and monthly averages
    total_consumption = sum(float(event.quantity_used) for event in usage_events)
    days_covered = (timezone.now().date() - usage_events.first().event_date.date()).days
    
    if days_covered > 0:
        daily_avg = total_consumption / days_covered
        pattern.average_consumption_per_week = Decimal(str(daily_avg * 7))
        pattern.average_consumption_per_month = Decimal(str(daily_avg * 30))
    
    # Calculate seasonal multipliers
    _calculate_seasonal_multipliers(pattern, usage_events)
    
    # Calculate purchase patterns
    _calculate_purchase_patterns(pattern)
    
    # Update confidence level
    pattern.confidence_level = _calculate_confidence_level(pattern)
    
    # Predict next reorder date
    pattern.next_reorder_prediction = _predict_next_reorder_date(pattern)
    
    pattern.save()
    
    return pattern


def _calculate_seasonal_multipliers(pattern, usage_events):
    """Calculate seasonal consumption multipliers."""
    seasonal_consumption = {'winter': [], 'spring': [], 'summer': [], 'fall': []}
    
    for event in usage_events:
        month = event.event_date.month
        consumption = float(event.quantity_used)
        
        if month in [12, 1, 2]:  # Winter
            seasonal_consumption['winter'].append(consumption)
        elif month in [3, 4, 5]:  # Spring
            seasonal_consumption['spring'].append(consumption)
        elif month in [6, 7, 8]:  # Summer
            seasonal_consumption['summer'].append(consumption)
        else:  # Fall
            seasonal_consumption['fall'].append(consumption)
    
    # Calculate averages and multipliers
    overall_avg = sum(sum(season_data) for season_data in seasonal_consumption.values()) / sum(len(season_data) for season_data in seasonal_consumption.values()) if any(seasonal_consumption.values()) else 1
    
    if overall_avg > 0:
        for season, consumption_data in seasonal_consumption.items():
            if consumption_data:
                season_avg = statistics.mean(consumption_data)
                multiplier = season_avg / overall_avg
                setattr(pattern, f'{season}_multiplier', Decimal(str(multiplier)))
            else:
                setattr(pattern, f'{season}_multiplier', Decimal('1.00'))


def _calculate_purchase_patterns(pattern):
    """Calculate typical purchase patterns from inventory items."""
    # Get recent inventory additions for this product
    recent_additions = InventoryItem.objects.filter(
        user=pattern.user,
        product=pattern.product,
        created_at__gte=timezone.now() - timedelta(days=180)
    ).order_by('created_at')
    
    if recent_additions.exists():
        # Calculate typical purchase quantity
        quantities = [float(item.quantity) for item in recent_additions]
        pattern.typical_purchase_quantity = Decimal(str(statistics.median(quantities)))
        
        # Calculate average days between purchases
        if recent_additions.count() > 1:
            purchase_intervals = []
            prev_date = None
            for item in recent_additions:
                if prev_date:
                    interval = (item.created_at.date() - prev_date).days
                    purchase_intervals.append(interval)
                prev_date = item.created_at.date()
            
            if purchase_intervals:
                pattern.average_days_between_purchases = int(statistics.median(purchase_intervals))


def _calculate_confidence_level(pattern) -> str:
    """Calculate confidence level based on data quality."""
    if pattern.data_points_count >= 10:
        return 'high'
    elif pattern.data_points_count >= 5:
        return 'medium'
    else:
        return 'low'


def _predict_next_reorder_date(pattern) -> Optional[date]:
    """Predict when the product should be reordered next."""
    if not pattern.is_reliable:
        return None
    
    # Get current inventory level
    current_inventory = InventoryItem.objects.filter(
        user=pattern.user,
        product=pattern.product,
        is_consumed=False
    ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')
    
    if current_inventory <= 0:
        return timezone.now().date()  # Reorder now
    
    # Calculate daily consumption rate
    daily_consumption = float(pattern.average_consumption_per_week) / 7
    
    if daily_consumption <= 0:
        return None
    
    # Apply seasonal adjustment
    current_season = _get_current_season()
    seasonal_multiplier = getattr(pattern, f'{current_season}_multiplier', Decimal('1.00'))
    adjusted_daily_consumption = daily_consumption * float(seasonal_multiplier)
    
    # Calculate days until inventory runs out
    days_until_empty = float(current_inventory) / adjusted_daily_consumption
    
    # Suggest reorder when 25% remains or 3 days before running out, whichever is sooner
    reorder_threshold_days = min(days_until_empty * 0.75, days_until_empty - 3)
    
    if reorder_threshold_days <= 0:
        return timezone.now().date()
    
    return timezone.now().date() + timedelta(days=int(reorder_threshold_days))


def _get_current_season() -> str:
    """Get current season based on month."""
    month = timezone.now().month
    if month in [12, 1, 2]:
        return 'winter'
    elif month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    else:
        return 'fall'


def generate_reorder_predictions(user, days_ahead: int = 30) -> List[ReorderPrediction]:
    """
    Generate reorder predictions for a user.
    
    Args:
        user: User to generate predictions for
        days_ahead: How many days ahead to predict
    
    Returns:
        List of ReorderPrediction instances
    """
    predictions = []
    cutoff_date = timezone.now().date() + timedelta(days=days_ahead)
    
    # Get reliable consumption patterns
    patterns = ConsumptionPattern.objects.filter(
        user=user,
        confidence_level__in=['medium', 'high'],
        next_reorder_prediction__isnull=False,
        next_reorder_prediction__lte=cutoff_date
    )
    
    for pattern in patterns:
        # Check if prediction already exists
        existing_prediction = ReorderPrediction.objects.filter(
            user=user,
            product=pattern.product,
            status__in=['pending', 'active'],
            predicted_reorder_date__gte=timezone.now().date()
        ).first()
        
        if existing_prediction:
            continue
        
        # Calculate predicted quantity
        predicted_quantity = _calculate_predicted_quantity(pattern)
        confidence_score = _calculate_prediction_confidence(pattern)
        
        prediction = ReorderPrediction.objects.create(
            user=user,
            product=pattern.product,
            consumption_pattern=pattern,
            predicted_reorder_date=pattern.next_reorder_prediction,
            predicted_quantity=predicted_quantity,
            unit=pattern.consumption_unit,
            confidence_score=confidence_score,
            status='pending'
        )
        
        predictions.append(prediction)
    
    return predictions


def _calculate_predicted_quantity(pattern) -> Decimal:
    """Calculate predicted reorder quantity."""
    # Base on typical purchase quantity and consumption rate
    base_quantity = pattern.typical_purchase_quantity
    
    # Adjust based on consumption rate
    if pattern.average_days_between_purchases > 0:
        days_worth = pattern.average_days_between_purchases
        daily_consumption = float(pattern.average_consumption_per_week) / 7
        needed_quantity = daily_consumption * days_worth
        
        # Take the larger of typical purchase or calculated need
        return max(base_quantity, Decimal(str(needed_quantity)))
    
    return base_quantity


def _calculate_prediction_confidence(pattern) -> Decimal:
    """Calculate confidence score for prediction."""
    base_confidence = Decimal('0.5')
    
    # Boost confidence based on data points
    if pattern.data_points_count >= 15:
        base_confidence += Decimal('0.3')
    elif pattern.data_points_count >= 10:
        base_confidence += Decimal('0.2')
    elif pattern.data_points_count >= 5:
        base_confidence += Decimal('0.1')
    
    # Boost confidence based on prediction accuracy
    if pattern.prediction_accuracy_score > Decimal('0.8'):
        base_confidence += Decimal('0.2')
    elif pattern.prediction_accuracy_score > Decimal('0.6'):
        base_confidence += Decimal('0.1')
    
    return min(base_confidence, Decimal('1.0'))


def update_budget_tracking(user, period_type: str = 'monthly') -> BudgetTracking:
    """
    Update budget tracking for the current period.
    
    Args:
        user: User to update budget for
        period_type: Type of period (weekly, monthly, quarterly, yearly)
    
    Returns:
        Updated BudgetTracking instance
    """
    today = timezone.now().date()
    
    # Calculate period dates
    if period_type == 'weekly':
        period_start = today - timedelta(days=today.weekday())
        period_end = period_start + timedelta(days=6)
    elif period_type == 'monthly':
        period_start = today.replace(day=1)
        _, last_day = monthrange(today.year, today.month)
        period_end = today.replace(day=last_day)
    elif period_type == 'quarterly':
        quarter = (today.month - 1) // 3 + 1
        period_start = date(today.year, (quarter - 1) * 3 + 1, 1)
        if quarter == 4:
            period_end = date(today.year, 12, 31)
        else:
            next_quarter_start = date(today.year, quarter * 3 + 1, 1)
            period_end = next_quarter_start - timedelta(days=1)
    else:  # yearly
        period_start = date(today.year, 1, 1)
        period_end = date(today.year, 12, 31)
    
    # Get or create budget tracking
    budget_tracking, created = BudgetTracking.objects.get_or_create(
        user=user,
        period_type=period_type,
        period_start=period_start,
        defaults={
            'period_end': period_end,
            'budget_amount': Decimal('500.00'),  # Default budget
        }
    )
    
    # Calculate actual spending from inventory items
    inventory_spending = InventoryItem.objects.filter(
        user=user,
        purchase_date__gte=period_start,
        purchase_date__lte=period_end,
        price__isnull=False
    )
    
    budget_tracking.actual_spent = inventory_spending.aggregate(
        total=Sum('price')
    )['total'] or Decimal('0.00')
    
    # Calculate category spending
    _calculate_category_spending(budget_tracking, inventory_spending)
    
    # Calculate variance and utilization
    budget_tracking.calculate_variance()
    
    return budget_tracking


def _calculate_category_spending(budget_tracking, inventory_spending):
    """Calculate spending by category."""
    category_spending = inventory_spending.values(
        'product__category__name'
    ).annotate(
        total=Sum('price')
    )
    
    # Reset category spending
    budget_tracking.produce_spent = Decimal('0.00')
    budget_tracking.dairy_spent = Decimal('0.00')
    budget_tracking.meat_spent = Decimal('0.00')
    budget_tracking.pantry_spent = Decimal('0.00')
    budget_tracking.other_spent = Decimal('0.00')
    
    # Map spending to categories
    category_mapping = {
        'produce': 'produce_spent',
        'dairy': 'dairy_spent',
        'meat': 'meat_spent',
        'pantry': 'pantry_spent',
    }
    
    for spending in category_spending:
        category_name = spending['product__category__name']
        if not category_name:
            category_name = 'other'
        
        category_name_lower = category_name.lower()
        field_name = category_mapping.get(category_name_lower, 'other_spent')
        
        current_value = getattr(budget_tracking, field_name)
        setattr(budget_tracking, field_name, current_value + (spending['total'] or Decimal('0.00')))


def get_usage_analytics(user, days: int = 30) -> Dict:
    """
    Get comprehensive usage analytics for a user.
    
    Args:
        user: User to analyze
        days: Number of days to look back
    
    Returns:
        Dictionary with usage analytics
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Get usage events
    usage_events = UsageEvent.objects.filter(
        user=user,
        event_date__gte=cutoff_date
    ).select_related('product')
    
    # Most used products
    most_used = usage_events.values(
        'product__name'
    ).annotate(
        total_usage=Sum('quantity_used'),
        usage_count=Count('id')
    ).order_by('-total_usage')[:10]
    
    # Usage by category
    usage_by_category = usage_events.values(
        'product__category__name'
    ).annotate(
        total_usage=Sum('quantity_used'),
        usage_count=Count('id')
    ).order_by('-total_usage')
    
    # Usage trends (weekly)
    usage_trends = []
    for week in range(4):  # Last 4 weeks
        week_start = timezone.now() - timedelta(weeks=week+1)
        week_end = timezone.now() - timedelta(weeks=week)
        
        week_usage = usage_events.filter(
            event_date__gte=week_start,
            event_date__lt=week_end
        )
        
        usage_trends.append({
            'week': week + 1,
            'start_date': week_start.date(),
            'end_date': week_end.date(),
            'total_events': week_usage.count(),
            'unique_products': week_usage.values('product').distinct().count(),
        })
    
    # Cooking frequency
    cooking_events = usage_events.filter(event_type='cooking_session')
    recipes_cooked = cooking_events.values('recipe').distinct().count()
    
    return {
        'period_days': days,
        'total_usage_events': usage_events.count(),
        'unique_products_used': usage_events.values('product').distinct().count(),
        'most_used_products': list(most_used),
        'usage_by_category': list(usage_by_category),
        'weekly_trends': usage_trends,
        'cooking_frequency': {
            'total_cooking_events': cooking_events.count(),
            'recipes_cooked': recipes_cooked,
            'avg_cooking_per_week': cooking_events.count() / 4 if cooking_events.count() > 0 else 0,
        },
        'reorder_predictions': ReorderPrediction.objects.filter(
            user=user,
            status='pending'
        ).count(),
    }