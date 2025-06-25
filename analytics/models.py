"""
Analytics models for tracking usage patterns and generating insights.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal

User = get_user_model()


class ConsumptionPattern(models.Model):
    """
    Track consumption patterns for products to predict reorder needs.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='consumption_patterns'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='consumption_patterns'
    )
    
    # Pattern metrics
    average_consumption_per_week = models.DecimalField(
        _('average weekly consumption'),
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000')
    )
    average_consumption_per_month = models.DecimalField(
        _('average monthly consumption'),
        max_digits=10,
        decimal_places=3,
        default=Decimal('0.000')
    )
    consumption_unit = models.CharField(_('consumption unit'), max_length=10, default='count')
    
    # Purchase patterns
    typical_purchase_quantity = models.DecimalField(
        _('typical purchase quantity'),
        max_digits=10,
        decimal_places=3,
        default=Decimal('1.000')
    )
    average_days_between_purchases = models.IntegerField(
        _('average days between purchases'),
        default=30
    )
    
    # Seasonal adjustments
    winter_multiplier = models.DecimalField(
        _('winter consumption multiplier'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )
    spring_multiplier = models.DecimalField(
        _('spring consumption multiplier'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )
    summer_multiplier = models.DecimalField(
        _('summer consumption multiplier'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )
    fall_multiplier = models.DecimalField(
        _('fall consumption multiplier'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00')
    )
    
    # Prediction accuracy
    prediction_accuracy_score = models.DecimalField(
        _('prediction accuracy score'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('0.00 to 1.00, higher is better')
    )
    
    # Data quality
    data_points_count = models.IntegerField(_('data points count'), default=0)
    confidence_level = models.CharField(
        _('confidence level'),
        max_length=10,
        choices=(
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
        ),
        default='low'
    )
    
    # Timing
    last_calculated = models.DateTimeField(_('last calculated'), auto_now=True)
    next_reorder_prediction = models.DateField(_('next reorder prediction'), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'consumption_patterns'
        verbose_name = _('consumption pattern')
        verbose_name_plural = _('consumption patterns')
        unique_together = ['user', 'product']
        indexes = [
            models.Index(fields=['user', 'next_reorder_prediction']),
            models.Index(fields=['confidence_level', 'prediction_accuracy_score']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} consumption pattern"
    
    @property
    def is_reliable(self):
        """Check if pattern data is reliable for predictions."""
        return (self.data_points_count >= 3 and 
                self.confidence_level in ['medium', 'high'] and
                self.prediction_accuracy_score >= Decimal('0.6'))


class UsageEvent(models.Model):
    """
    Track individual usage events for analytics.
    """
    EVENT_TYPES = (
        ('cooking_session', _('Cooking Session')),
        ('manual_consumption', _('Manual Consumption')),
        ('inventory_adjustment', _('Inventory Adjustment')),
        ('recipe_cooking', _('Recipe Cooking')),
        ('waste_logged', _('Waste Logged')),
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='usage_events'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='usage_events'
    )
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_events'
    )
    
    # Event details
    event_type = models.CharField(
        _('event type'),
        max_length=20,
        choices=EVENT_TYPES
    )
    quantity_used = models.DecimalField(
        _('quantity used'),
        max_digits=10,
        decimal_places=3
    )
    unit = models.CharField(_('unit'), max_length=10)
    
    # Context
    recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_events'
    )
    cooking_session = models.ForeignKey(
        'recipes.CookingSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usage_events'
    )
    
    # Metadata
    event_date = models.DateTimeField(_('event date'), default=timezone.now)
    notes = models.TextField(_('notes'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'usage_events'
        verbose_name = _('usage event')
        verbose_name_plural = _('usage events')
        ordering = ['-event_date']
        indexes = [
            models.Index(fields=['user', 'event_date']),
            models.Index(fields=['product', 'event_type']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()}: {self.quantity_used} {self.unit} of {self.product.name}"


class BudgetTracking(models.Model):
    """
    Track spending patterns and budget performance.
    """
    PERIOD_TYPES = (
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('yearly', _('Yearly')),
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='budget_trackings'
    )
    
    # Period definition
    period_type = models.CharField(
        _('period type'),
        max_length=10,
        choices=PERIOD_TYPES
    )
    period_start = models.DateField(_('period start'))
    period_end = models.DateField(_('period end'))
    
    # Budget vs actual
    budget_amount = models.DecimalField(
        _('budget amount'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    actual_spent = models.DecimalField(
        _('actual spent'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Category breakdown
    produce_budget = models.DecimalField(_('produce budget'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    produce_spent = models.DecimalField(_('produce spent'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    dairy_budget = models.DecimalField(_('dairy budget'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    dairy_spent = models.DecimalField(_('dairy spent'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    meat_budget = models.DecimalField(_('meat budget'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    meat_spent = models.DecimalField(_('meat spent'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    pantry_budget = models.DecimalField(_('pantry budget'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pantry_spent = models.DecimalField(_('pantry spent'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    other_budget = models.DecimalField(_('other budget'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    other_spent = models.DecimalField(_('other spent'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Performance metrics
    budget_variance = models.DecimalField(
        _('budget variance'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_('Positive = under budget, Negative = over budget')
    )
    budget_utilization_percentage = models.DecimalField(
        _('budget utilization percentage'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'budget_tracking'
        verbose_name = _('budget tracking')
        verbose_name_plural = _('budget tracking')
        unique_together = ['user', 'period_type', 'period_start']
        ordering = ['-period_start']
    
    def __str__(self):
        return f"{self.user.username} {self.get_period_type_display()} budget ({self.period_start})"
    
    def calculate_variance(self):
        """Calculate budget variance and utilization."""
        self.budget_variance = self.budget_amount - self.actual_spent
        if self.budget_amount > 0:
            self.budget_utilization_percentage = (self.actual_spent / self.budget_amount) * 100
        else:
            self.budget_utilization_percentage = Decimal('0.00')
        self.save(update_fields=['budget_variance', 'budget_utilization_percentage'])
    
    @property
    def is_over_budget(self):
        """Check if spending is over budget."""
        return self.actual_spent > self.budget_amount
    
    @property
    def remaining_budget(self):
        """Get remaining budget amount."""
        return max(Decimal('0.00'), self.budget_amount - self.actual_spent)


class ReorderPrediction(models.Model):
    """
    Predictions for when items should be reordered.
    """
    PREDICTION_STATUS = (
        ('pending', _('Pending')),
        ('active', _('Active')),
        ('fulfilled', _('Fulfilled')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled')),
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reorder_predictions'
    )
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        related_name='reorder_predictions'
    )
    consumption_pattern = models.ForeignKey(
        ConsumptionPattern,
        on_delete=models.CASCADE,
        related_name='reorder_predictions'
    )
    
    # Prediction details
    predicted_reorder_date = models.DateField(_('predicted reorder date'))
    predicted_quantity = models.DecimalField(
        _('predicted quantity'),
        max_digits=10,
        decimal_places=3
    )
    unit = models.CharField(_('unit'), max_length=10)
    
    # Confidence and accuracy
    confidence_score = models.DecimalField(
        _('confidence score'),
        max_digits=5,
        decimal_places=2,
        help_text=_('0.00 to 1.00, higher is better')
    )
    
    # Actual vs predicted (filled when fulfilled)
    actual_reorder_date = models.DateField(_('actual reorder date'), null=True, blank=True)
    actual_quantity = models.DecimalField(
        _('actual quantity'),
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True
    )
    accuracy_score = models.DecimalField(
        _('accuracy score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Calculated after fulfillment')
    )
    
    # Status tracking
    status = models.CharField(
        _('status'),
        max_length=10,
        choices=PREDICTION_STATUS,
        default='pending'
    )
    
    # Integration with shopping lists
    shopping_list_item = models.ForeignKey(
        'shopping.ShoppingListItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reorder_predictions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'reorder_predictions'
        verbose_name = _('reorder prediction')
        verbose_name_plural = _('reorder predictions')
        ordering = ['predicted_reorder_date']
        indexes = [
            models.Index(fields=['user', 'status', 'predicted_reorder_date']),
            models.Index(fields=['product', 'status']),
        ]
    
    def __str__(self):
        return f"Reorder {self.product.name} by {self.predicted_reorder_date}"
    
    def fulfill(self, actual_date, actual_quantity):
        """Mark prediction as fulfilled and calculate accuracy."""
        self.status = 'fulfilled'
        self.actual_reorder_date = actual_date
        self.actual_quantity = actual_quantity
        
        # Calculate accuracy score
        date_accuracy = self._calculate_date_accuracy()
        quantity_accuracy = self._calculate_quantity_accuracy()
        self.accuracy_score = (date_accuracy + quantity_accuracy) / 2
        
        self.save()
        
        # Update consumption pattern accuracy
        self.consumption_pattern.prediction_accuracy_score = self._update_pattern_accuracy()
        self.consumption_pattern.save()
    
    def _calculate_date_accuracy(self):
        """Calculate accuracy of date prediction."""
        if not self.actual_reorder_date:
            return Decimal('0.00')
        
        days_diff = abs((self.actual_reorder_date - self.predicted_reorder_date).days)
        
        # Perfect accuracy within 1 day, decreasing by 10% per day
        if days_diff == 0:
            return Decimal('1.00')
        elif days_diff <= 7:
            return max(Decimal('0.00'), Decimal('1.00') - (Decimal(str(days_diff)) * Decimal('0.1')))
        else:
            return Decimal('0.00')
    
    def _calculate_quantity_accuracy(self):
        """Calculate accuracy of quantity prediction."""
        if not self.actual_quantity or self.predicted_quantity == 0:
            return Decimal('0.00')
        
        ratio = min(self.actual_quantity, self.predicted_quantity) / max(self.actual_quantity, self.predicted_quantity)
        return ratio
    
    def _update_pattern_accuracy(self):
        """Update overall pattern accuracy based on recent predictions."""
        recent_predictions = ReorderPrediction.objects.filter(
            consumption_pattern=self.consumption_pattern,
            status='fulfilled',
            accuracy_score__isnull=False
        ).order_by('-created_at')[:10]  # Last 10 predictions
        
        if recent_predictions:
            avg_accuracy = sum(p.accuracy_score for p in recent_predictions) / len(recent_predictions)
            return avg_accuracy
        
        return self.consumption_pattern.prediction_accuracy_score