"""
Shopping list models for managing grocery lists and shopping workflows.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class Store(models.Model):
    """
    Store model for associating shopping lists with specific stores.
    """
    name = models.CharField(_('store name'), max_length=200, unique=True)
    slug = models.SlugField(_('slug'), unique=True, blank=True)
    address = models.TextField(_('address'), blank=True)
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    website = models.URLField(_('website'), blank=True)
    
    # Store layout sections for optimization
    sections = models.JSONField(
        _('store sections'),
        default=list,
        help_text=_('List of store sections in order (e.g., ["Produce", "Dairy", "Meat", "Bakery"])')
    )
    
    # Store characteristics
    store_type = models.CharField(
        _('store type'),
        max_length=50,
        choices=[
            ('grocery', _('Grocery Store')),
            ('supermarket', _('Supermarket')),
            ('convenience', _('Convenience Store')),
            ('warehouse', _('Warehouse Store')),
            ('specialty', _('Specialty Store')),
            ('other', _('Other')),
        ],
        default='grocery'
    )
    is_chain = models.BooleanField(_('is chain store'), default=False)
    chain_name = models.CharField(_('chain name'), max_length=100, blank=True)
    
    # Location data
    latitude = models.DecimalField(
        _('latitude'), 
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        _('longitude'), 
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stores'
        verbose_name = _('store')
        verbose_name_plural = _('stores')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Store.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    @property
    def default_sections(self):
        """Get default store sections if none are defined."""
        if self.sections:
            return self.sections
        return [
            'Produce', 'Dairy', 'Meat & Seafood', 'Deli', 'Bakery',
            'Pantry', 'Frozen', 'Beverages', 'Snacks', 'Health & Beauty',
            'Household', 'Other'
        ]


class ShoppingList(models.Model):
    """
    Shopping list model for managing grocery lists.
    """
    STATUS_CHOICES = (
        ('active', _('Active')),
        ('shopping', _('Shopping')),
        ('completed', _('Completed')),
        ('archived', _('Archived')),
    )
    
    GENERATION_SOURCES = (
        ('manual', _('Manual')),
        ('recipe', _('Recipe')),
        ('depletion', _('Inventory Depletion')),
        ('recurring', _('Recurring Items')),
        ('smart', _('Smart Suggestions')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(_('list name'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    
    # Ownership and sharing
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_shopping_lists',
        verbose_name=_('created by')
    )
    household = models.ForeignKey(
        'accounts.Household',
        on_delete=models.CASCADE,
        related_name='shopping_lists',
        verbose_name=_('household')
    )
    shared_with = models.ManyToManyField(
        User,
        through='ShoppingListShare',
        through_fields=('shopping_list', 'user'),
        related_name='shared_shopping_lists',
        blank=True
    )
    
    # Status and metadata
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    generation_source = models.CharField(
        _('generation source'),
        max_length=20,
        choices=GENERATION_SOURCES,
        default='manual'
    )
    
    # Store association
    store = models.ForeignKey(
        Store,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopping_lists'
    )
    
    # Shopping session data
    shopping_started_at = models.DateTimeField(_('shopping started'), null=True, blank=True)
    shopping_completed_at = models.DateTimeField(_('shopping completed'), null=True, blank=True)
    
    # Budgeting
    budget_limit = models.DecimalField(
        _('budget limit'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    estimated_total = models.DecimalField(
        _('estimated total'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    actual_total = models.DecimalField(
        _('actual total'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Optimization flags
    is_optimized = models.BooleanField(_('optimized for store layout'), default=False)
    auto_update = models.BooleanField(_('auto-update from inventory'), default=True)
    
    # Recurring list settings
    is_recurring = models.BooleanField(_('recurring list'), default=False)
    recurrence_interval = models.IntegerField(
        _('recurrence interval (days)'),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    last_generated = models.DateTimeField(_('last generated'), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopping_lists'
        verbose_name = _('shopping list')
        verbose_name_plural = _('shopping lists')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['store', 'status']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def total_items(self):
        """Get total number of items in the list."""
        return self.items.count()
    
    @property
    def completed_items(self):
        """Get number of completed items."""
        return self.items.filter(is_purchased=True).count()
    
    @property
    def remaining_items(self):
        """Get number of remaining items."""
        return self.items.filter(is_purchased=False).count()
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage."""
        if self.total_items == 0:
            return 0
        return (self.completed_items / self.total_items) * 100
    
    @property
    def is_shopping_active(self):
        """Check if shopping session is active."""
        return self.status == 'shopping' and self.shopping_started_at and not self.shopping_completed_at
    
    def start_shopping(self):
        """Start a shopping session."""
        self.status = 'shopping'
        self.shopping_started_at = timezone.now()
        self.save(update_fields=['status', 'shopping_started_at'])
    
    def complete_shopping(self, actual_total=None):
        """Complete a shopping session."""
        self.status = 'completed'
        self.shopping_completed_at = timezone.now()
        if actual_total is not None:
            self.actual_total = actual_total
        self.save(update_fields=['status', 'shopping_completed_at', 'actual_total'])
    
    def calculate_estimated_total(self):
        """Calculate estimated total from item prices."""
        total = Decimal('0.00')
        for item in self.items.all():
            if item.estimated_price and item.quantity:
                total += item.estimated_price * Decimal(str(item.quantity))
        
        self.estimated_total = total
        self.save(update_fields=['estimated_total'])
        return total
    
    def optimize_for_store(self):
        """Optimize item order based on store layout."""
        if not self.store or not self.store.sections:
            return
        
        # Get store sections
        sections = self.store.default_sections
        
        # Update item orders based on store sections
        section_order = {section: idx for idx, section in enumerate(sections)}
        
        for item in self.items.all():
            if item.category:
                # Map item category to store section
                item.store_section = self._map_category_to_section(item.category, sections)
                item.section_order = section_order.get(item.store_section, 999)
                item.save(update_fields=['store_section', 'section_order'])
        
        self.is_optimized = True
        self.save(update_fields=['is_optimized'])
    
    def _map_category_to_section(self, category, sections):
        """Map inventory category to store section."""
        category_mapping = {
            'fruits': 'Produce',
            'vegetables': 'Produce',
            'dairy': 'Dairy',
            'meat': 'Meat & Seafood',
            'seafood': 'Meat & Seafood',
            'bakery': 'Bakery',
            'frozen': 'Frozen',
            'beverages': 'Beverages',
            'snacks': 'Snacks',
            'pantry': 'Pantry',
            'spices': 'Pantry',
            'condiments': 'Pantry',
        }
        
        category_name = category.lower() if category else ''
        return category_mapping.get(category_name, 'Other')


class ShoppingListItem(models.Model):
    """
    Individual items in a shopping list.
    """
    PRIORITY_CHOICES = (
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    )
    
    shopping_list = models.ForeignKey(
        ShoppingList,
        on_delete=models.CASCADE,
        related_name='items'
    )
    
    # Product information
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='shopping_list_items'
    )
    name = models.CharField(_('item name'), max_length=200)
    notes = models.TextField(_('notes'), blank=True)
    
    # Quantity and pricing
    quantity = models.DecimalField(
        _('quantity'),
        max_digits=10,
        decimal_places=3,
        default=Decimal('1.000'),
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    unit = models.CharField(_('unit'), max_length=50, blank=True)
    
    estimated_price = models.DecimalField(
        _('estimated price'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    actual_price = models.DecimalField(
        _('actual price'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Organization
    category = models.CharField(_('category'), max_length=100, blank=True)
    store_section = models.CharField(_('store section'), max_length=100, blank=True)
    section_order = models.IntegerField(_('section order'), default=0)
    custom_order = models.IntegerField(_('custom order'), default=0)
    
    # Status and metadata
    is_purchased = models.BooleanField(_('purchased'), default=False)
    purchased_at = models.DateTimeField(_('purchased at'), null=True, blank=True)
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal'
    )
    
    # Generation metadata
    added_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_shopping_items'
    )
    source_recipe = models.ForeignKey(
        'recipes.Recipe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shopping_list_items'
    )
    is_recurring = models.BooleanField(_('recurring item'), default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shopping_list_items'
        verbose_name = _('shopping list item')
        verbose_name_plural = _('shopping list items')
        ordering = ['section_order', 'custom_order', 'name']
        indexes = [
            models.Index(fields=['shopping_list', 'is_purchased']),
            models.Index(fields=['section_order', 'custom_order']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.quantity} {self.unit}"
    
    @property
    def total_cost(self):
        """Calculate total cost based on quantity and price."""
        price = self.actual_price or self.estimated_price
        if price and self.quantity:
            return price * self.quantity
        return None
    
    def mark_purchased(self, actual_price=None):
        """Mark item as purchased."""
        self.is_purchased = True
        self.purchased_at = timezone.now()
        if actual_price is not None:
            self.actual_price = actual_price
        self.save(update_fields=['is_purchased', 'purchased_at', 'actual_price'])
    
    def mark_unpurchased(self):
        """Mark item as not purchased."""
        self.is_purchased = False
        self.purchased_at = None
        self.actual_price = None
        self.save(update_fields=['is_purchased', 'purchased_at', 'actual_price'])
    
    @property
    def estimated_total(self):
        """Get estimated total cost for this item."""
        if self.estimated_price and self.quantity:
            return self.estimated_price * Decimal(str(self.quantity))
        return Decimal('0.00')
    
    @property
    def actual_total(self):
        """Get actual total cost for this item."""
        if self.actual_price and self.quantity:
            return self.actual_price * Decimal(str(self.quantity))
        return Decimal('0.00')


class ShoppingListShare(models.Model):
    """
    Through model for sharing shopping lists between users.
    """
    PERMISSION_CHOICES = (
        ('view', _('View Only')),
        ('edit', _('Can Edit')),
        ('admin', _('Admin')),
    )
    
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    permission = models.CharField(
        _('permission'),
        max_length=10,
        choices=PERMISSION_CHOICES,
        default='view'
    )
    
    shared_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_shares_created'
    )
    shared_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'shopping_list_shares'
        verbose_name = _('shopping list share')
        verbose_name_plural = _('shopping list shares')
        unique_together = ['shopping_list', 'user']
    
    def __str__(self):
        return f"{self.shopping_list.name} shared with {self.user.username}"
    
    @property
    def can_edit(self):
        """Check if user can edit the shopping list."""
        return self.permission in ['edit', 'admin']


class RecurringShoppingItem(models.Model):
    """
    Template for recurring shopping list items.
    """
    FREQUENCY_CHOICES = (
        ('weekly', _('Weekly')),
        ('biweekly', _('Bi-weekly')),
        ('monthly', _('Monthly')),
        ('custom', _('Custom')),
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recurring_shopping_items'
    )
    household = models.ForeignKey(
        'accounts.Household',
        on_delete=models.CASCADE,
        related_name='recurring_shopping_items',
        null=True,
        blank=True
    )
    
    # Item details
    product = models.ForeignKey(
        'inventory.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    name = models.CharField(_('item name'), max_length=200)
    quantity = models.DecimalField(
        _('quantity'),
        max_digits=10,
        decimal_places=3,
        default=Decimal('1.000')
    )
    unit = models.CharField(_('unit'), max_length=50, blank=True)
    
    # Recurrence settings
    frequency = models.CharField(
        _('frequency'),
        max_length=10,
        choices=FREQUENCY_CHOICES,
        default='weekly'
    )
    custom_days = models.IntegerField(
        _('custom frequency (days)'),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(365)]
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    last_added = models.DateTimeField(_('last added'), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recurring_shopping_items'
        verbose_name = _('recurring shopping item')
        verbose_name_plural = _('recurring shopping items')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.quantity} {self.unit} ({self.frequency})"
    
    @property
    def last_added_date(self):
        """Alias for last_added for test compatibility."""
        return self.last_added.date() if self.last_added else None
    
    @last_added_date.setter
    def last_added_date(self, value):
        """Set last_added from date value."""
        if value:
            from django.utils import timezone
            # Convert date to datetime
            self.last_added = timezone.make_aware(
                timezone.datetime.combine(value, timezone.datetime.min.time())
            )
        else:
            self.last_added = None
    
    @property
    def next_due_date(self):
        """Calculate next due date."""
        if not self.last_added:
            return timezone.now().date()
        
        from datetime import timedelta
        if self.frequency == 'weekly':
            return self.last_added.date() + timedelta(days=7)
        elif self.frequency == 'biweekly':
            return self.last_added.date() + timedelta(days=14)
        elif self.frequency == 'monthly':
            return self.last_added.date() + timedelta(days=30)
        elif self.frequency == 'custom' and self.custom_days:
            return self.last_added.date() + timedelta(days=self.custom_days)
        else:
            return self.last_added.date() + timedelta(days=7)
    
    @property
    def is_due(self):
        """Check if this recurring item is due."""
        if not self.last_added:
            return True
        return self.next_due_date <= timezone.now().date()
    
    def mark_added(self):
        """Mark this recurring item as added today."""
        self.last_added = timezone.now()
        self.save()
    
    @property
    def days_until_next(self):
        """Calculate days until next occurrence."""
        if not self.last_added:
            return 0
        
        frequency_days = {
            'weekly': 7,
            'biweekly': 14,
            'monthly': 30,
            'custom': self.custom_days or 7
        }
        
        days_since = (timezone.now().date() - self.last_added.date()).days
        interval = frequency_days[self.frequency]
        
        return max(0, interval - days_since)
    
