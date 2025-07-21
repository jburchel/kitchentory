from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid

User = get_user_model()


class SubscriptionPlan(models.Model):
    """
    Defines the available subscription tiers and their features.
    """
    TIER_CHOICES = [
        ('free', 'Free - Kitchen Starter'),
        ('premium', 'Premium - Kitchen Pro'),
        ('pro', 'Pro - Kitchen Master'),
    ]
    
    BILLING_PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    # Basic Information
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Pricing
    monthly_price = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    yearly_price = models.DecimalField(
        max_digits=6, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Feature Limits
    max_inventory_items = models.IntegerField(
        null=True, 
        blank=True,
        help_text="None means unlimited"
    )
    max_recipes_per_day = models.IntegerField(
        null=True,
        blank=True,
        help_text="None means unlimited"
    )
    max_shopping_lists = models.IntegerField(
        null=True,
        blank=True,
        help_text="None means unlimited"
    )
    max_household_members = models.IntegerField(default=1)
    max_saved_recipes = models.IntegerField(
        null=True,
        blank=True,
        help_text="None means unlimited"
    )
    
    # Feature Flags
    has_recipe_matching = models.BooleanField(default=False)
    has_advanced_matching = models.BooleanField(default=False)
    has_meal_planning = models.BooleanField(default=False)
    has_nutrition_tracking = models.BooleanField(default=False)
    has_analytics = models.BooleanField(default=False)
    has_advanced_analytics = models.BooleanField(default=False)
    has_export = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)
    has_ocr_receipts = models.BooleanField(default=False)
    has_voice_input = models.BooleanField(default=False)
    has_priority_support = models.BooleanField(default=False)
    
    # Metadata
    stripe_product_id = models.CharField(max_length=100, blank=True)
    stripe_monthly_price_id = models.CharField(max_length=100, blank=True)
    stripe_yearly_price_id = models.CharField(max_length=100, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscription_plans'
        ordering = ['monthly_price']
    
    def __str__(self):
        return f"{self.name} ({self.tier})"
    
    def get_price(self, billing_period='monthly'):
        """Get price based on billing period."""
        if billing_period == 'yearly':
            return self.yearly_price
        return self.monthly_price
    
    def get_stripe_price_id(self, billing_period='monthly'):
        """Get Stripe price ID based on billing period."""
        if billing_period == 'yearly':
            return self.stripe_yearly_price_id
        return self.stripe_monthly_price_id


class Subscription(models.Model):
    """
    Tracks user subscriptions and their status.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('trialing', 'Trialing'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
    ]
    
    # Relationships
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    
    # Subscription Details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    billing_period = models.CharField(
        max_length=10,
        choices=SubscriptionPlan.BILLING_PERIOD_CHOICES,
        default='monthly'
    )
    
    # Stripe Integration
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)
    
    # Important Dates
    trial_start = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField(default=timezone.now)
    current_period_end = models.DateTimeField()
    canceled_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subscriptions'
    
    def __str__(self):
        return f"{self.user.email} - {self.plan.name} ({self.status})"
    
    @property
    def is_active(self):
        """Check if subscription is currently active."""
        return self.status in ['active', 'trialing']
    
    @property
    def is_trialing(self):
        """Check if subscription is in trial period."""
        return (
            self.status == 'trialing' and 
            self.trial_end and 
            timezone.now() < self.trial_end
        )
    
    def cancel(self, immediately=False):
        """Cancel subscription."""
        self.canceled_at = timezone.now()
        if immediately:
            self.status = 'canceled'
            self.current_period_end = timezone.now()
        else:
            # Will cancel at end of billing period
            self.status = 'active'
        self.save()


class BillingHistory(models.Model):
    """
    Tracks all billing events and invoices.
    """
    TYPE_CHOICES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('credit', 'Credit'),
        ('adjustment', 'Adjustment'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Relationships
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='billing_history'
    )
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        related_name='billing_history'
    )
    
    # Transaction Details
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    
    # Stripe Integration
    stripe_invoice_id = models.CharField(max_length=100, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=100, blank=True)
    stripe_charge_id = models.CharField(max_length=100, blank=True)
    
    # Additional Info
    description = models.TextField(blank=True)
    invoice_url = models.URLField(blank=True)
    invoice_pdf = models.URLField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'billing_history'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.type} - ${self.amount}"


# Usage Tracking Models

class InventoryUsage(models.Model):
    """
    Tracks inventory item count per user for enforcing limits.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='inventory_usage'
    )
    item_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_usage'
    
    def __str__(self):
        return f"{self.user.email} - {self.item_count} items"
    
    def can_add_item(self):
        """Check if user can add more items based on their plan."""
        if not hasattr(self.user, 'subscription'):
            # Free plan by default
            plan = SubscriptionPlan.objects.get(tier='free')
        else:
            plan = self.user.subscription.plan
        
        if plan.max_inventory_items is None:
            return True
        
        return self.item_count < plan.max_inventory_items


class RecipeSearchUsage(models.Model):
    """
    Tracks daily recipe searches per user for enforcing limits.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipe_search_usage'
    )
    date = models.DateField(default=timezone.now)
    search_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'recipe_search_usage'
        unique_together = ['user', 'date']
    
    def __str__(self):
        return f"{self.user.email} - {self.date} - {self.search_count} searches"
    
    @classmethod
    def get_today_count(cls, user):
        """Get today's search count for a user."""
        usage, created = cls.objects.get_or_create(
            user=user,
            date=timezone.now().date()
        )
        return usage.search_count
    
    @classmethod
    def can_search(cls, user):
        """Check if user can perform more searches today."""
        if not hasattr(user, 'subscription'):
            # Free plan by default
            plan = SubscriptionPlan.objects.get(tier='free')
        else:
            plan = user.subscription.plan
        
        if plan.max_recipes_per_day is None:
            return True
        
        today_count = cls.get_today_count(user)
        return today_count < plan.max_recipes_per_day
    
    @classmethod
    def increment_search(cls, user):
        """Increment search count for user."""
        usage, created = cls.objects.get_or_create(
            user=user,
            date=timezone.now().date()
        )
        usage.search_count += 1
        usage.save()
        return usage.search_count


class ShoppingListUsage(models.Model):
    """
    Tracks shopping list count per user for enforcing limits.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_list_usage'
    )
    list_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopping_list_usage'
    
    def __str__(self):
        return f"{self.user.email} - {self.list_count} lists"
    
    def can_create_list(self):
        """Check if user can create more shopping lists."""
        if not hasattr(self.user, 'subscription'):
            # Free plan by default
            plan = SubscriptionPlan.objects.get(tier='free')
        else:
            plan = self.user.subscription.plan
        
        if plan.max_shopping_lists is None:
            return True
        
        return self.list_count < plan.max_shopping_lists


class ExportUsage(models.Model):
    """
    Tracks data exports per user.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='export_usage'
    )
    export_type = models.CharField(max_length=50)
    export_format = models.CharField(max_length=20)
    item_count = models.IntegerField(default=0)
    file_size = models.IntegerField(default=0, help_text="Size in bytes")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'export_usage'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.export_type} - {self.created_at}"