from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid

User = get_user_model()


class InventoryItemQuerySet(models.QuerySet):
    """Custom QuerySet for InventoryItem."""
    
    def expired(self):
        """Return items that are expired."""
        from django.utils import timezone
        return self.filter(
            expiration_date__lt=timezone.now().date(),
            is_consumed=False
        )
    
    def expiring_soon(self, days=7):
        """Return items expiring within specified days."""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now().date() + timedelta(days=days)
        return self.filter(
            expiration_date__lte=cutoff_date,
            expiration_date__gte=timezone.now().date(),
            is_consumed=False
        )
    
    def low_stock(self):
        """Return items that are low on stock."""
        return self.filter(
            current_quantity__lt=models.F('minimum_threshold'),
            is_consumed=False
        )


class Category(models.Model):
    """
    Product categories with hierarchical structure.
    """
    CATEGORY_COLORS = {
        'produce': '#84CC16',
        'dairy': '#60A5FA',
        'meat': '#F87171',
        'pantry': '#FBBF24',
        'frozen': '#A78BFA',
        'beverages': '#3B82F6',
        'snacks': '#F59E0B',
        'other': '#6B7280',
    }
    
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    slug = models.SlugField(_('slug'), unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )
    color = models.CharField(_('color'), max_length=7, default='#6B7280')
    icon = models.CharField(_('icon'), max_length=50, blank=True)
    order = models.IntegerField(_('display order'), default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'categories'
        verbose_name = _('category')
        verbose_name_plural = _('categories')
        ordering = ['order', 'name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        if not self.color and self.slug in self.CATEGORY_COLORS:
            self.color = self.CATEGORY_COLORS[self.slug]
        super().save(*args, **kwargs)


class StorageLocation(models.Model):
    """
    Storage locations within a household.
    """
    LOCATION_TYPES = (
        ('refrigerator', _('Refrigerator')),
        ('fridge', _('Refrigerator')),
        ('freezer', _('Freezer')),
        ('pantry', _('Pantry')),
        ('counter', _('Counter')),
        ('cabinet', _('Cabinet')),
        ('other', _('Other')),
    )
    
    household = models.ForeignKey(
        'accounts.Household',
        on_delete=models.CASCADE,
        related_name='storage_locations'
    )
    name = models.CharField(_('name'), max_length=100)
    location_type = models.CharField(
        _('type'),
        max_length=20,
        choices=LOCATION_TYPES,
        default='pantry'
    )
    temperature = models.FloatField(
        _('temperature (°C)'),
        null=True,
        blank=True,
        help_text=_('Average temperature for expiration calculations')
    )
    temperature_min = models.FloatField(
        _('minimum temperature (°C)'),
        null=True,
        blank=True
    )
    temperature_max = models.FloatField(
        _('maximum temperature (°C)'),
        null=True,
        blank=True
    )
    notes = models.TextField(_('notes'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'storage_locations'
        verbose_name = _('storage location')
        verbose_name_plural = _('storage locations')
        unique_together = ['household', 'name']
    
    def __str__(self):
        return self.name
    
    def clean(self):
        """Validate temperature range."""
        from django.core.exceptions import ValidationError
        
        if (self.temperature_min is not None and 
            self.temperature_max is not None and 
            self.temperature_min > self.temperature_max):
            raise ValidationError({
                'temperature_min': 'Minimum temperature cannot be greater than maximum temperature.'
            })


class Product(models.Model):
    """
    Global product database for barcode scanning and autocomplete.
    """
    barcode = models.CharField(
        _('barcode'),
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        db_index=True
    )
    name = models.CharField(_('name'), max_length=200, db_index=True)
    brand = models.CharField(_('brand'), max_length=100, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name='products'
    )
    
    # Nutritional information (optional)
    serving_size = models.CharField(_('serving size'), max_length=50, blank=True)
    calories = models.IntegerField(_('calories'), null=True, blank=True)
    
    # Images
    image_url = models.URLField(_('image URL'), blank=True, null=True)
    thumbnail_url = models.URLField(_('thumbnail URL'), blank=True, null=True)
    local_image = models.ImageField(_('local image'), upload_to='products/', blank=True, null=True)
    local_thumbnail = models.ImageField(_('local thumbnail'), upload_to='products/thumbs/', blank=True, null=True)
    
    # Extended product information
    description = models.TextField(_('description'), blank=True, default='')
    ingredients = models.TextField(_('ingredients'), blank=True, default='')
    packaging = models.CharField(_('packaging'), max_length=200, blank=True, default='')
    country = models.CharField(_('country'), max_length=100, blank=True, default='')
    
    # Default unit for this product
    default_unit = models.CharField(
        _('default unit'),
        max_length=10,
        choices=(
            ('count', _('Count')),
            ('g', _('Grams')),
            ('kg', _('Kilograms')),
            ('ml', _('Milliliters')),
            ('l', _('Liters')),
            ('oz', _('Ounces')),
            ('lb', _('Pounds')),
        ),
        default='count'
    )
    
    # Pricing information
    average_price = models.DecimalField(
        _('average price'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    shelf_life_days = models.IntegerField(
        _('shelf life (days)'),
        null=True,
        blank=True,
        help_text=_('Typical shelf life in days')
    )
    
    # Metadata
    source = models.CharField(
        _('data source'),
        max_length=50,
        blank=True,
        help_text=_('e.g., openfoodfacts, upcitemdb, manual')
    )
    verified = models.BooleanField(_('verified'), default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'products'
        verbose_name = _('product')
        verbose_name_plural = _('products')
        indexes = [
            models.Index(fields=['name', 'brand']),
        ]
    
    def __str__(self):
        if self.brand:
            return f"{self.brand} - {self.name}"
        return self.name
    
    @classmethod
    def search(cls, query):
        """Search products with fuzzy matching for typos"""
        if not query:
            return cls.objects.none()
        
        # First try exact matches
        exact_matches = cls._exact_search(query)
        if exact_matches.exists():
            return exact_matches
        
        # Then try fuzzy matching for typos
        return cls._fuzzy_search(query)
    
    @classmethod
    def _exact_search(cls, query):
        """Exact search matching"""
        words = query.strip().split()
        queryset = cls.objects.all()
        
        for word in words:
            queryset = queryset.filter(
                models.Q(name__icontains=word) |
                models.Q(brand__icontains=word) |
                models.Q(description__icontains=word)
            )
        
        return queryset.distinct().order_by('name')
    
    @classmethod
    def _fuzzy_search(cls, query):
        """Fuzzy search for handling typos"""
        from difflib import get_close_matches
        
        # Get all product names and brands for fuzzy matching
        all_products = cls.objects.values('id', 'name', 'brand')
        
        # Create searchable text list
        searchable_texts = []
        product_map = {}
        
        for product in all_products:
            # Add product name
            name = product['name'].lower()
            searchable_texts.append(name)
            product_map[name] = product['id']
            
            # Add brand if exists
            if product['brand']:
                brand = product['brand'].lower()
                searchable_texts.append(brand)
                product_map[brand] = product['id']
                
                # Add brand + name combination
                combo = f"{brand} {name}"
                searchable_texts.append(combo)
                product_map[combo] = product['id']
        
        # Find close matches with fuzzy matching
        query_lower = query.lower()
        close_matches = get_close_matches(
            query_lower, 
            searchable_texts, 
            n=10,  # Max 10 matches
            cutoff=0.4  # 40% similarity threshold
        )
        
        # Get product IDs from matches
        matched_product_ids = []
        for match in close_matches:
            if match in product_map:
                matched_product_ids.append(product_map[match])
        
        # Remove duplicates while preserving order
        unique_ids = []
        for pid in matched_product_ids:
            if pid not in unique_ids:
                unique_ids.append(pid)
        
        if unique_ids:
            # Return products ordered by match quality
            preserved_order = models.Case(
                *[models.When(pk=pk, then=pos) for pos, pk in enumerate(unique_ids)]
            )
            return cls.objects.filter(id__in=unique_ids).order_by(preserved_order)
        
        return cls.objects.none()


class InventoryItem(models.Model):
    """
    User's inventory items linked to products.
    """
    QUANTITY_UNITS = (
        ('count', _('Count')),
        ('g', _('Grams')),
        ('kg', _('Kilograms')),
        ('ml', _('Milliliters')),
        ('l', _('Liters')),
        ('oz', _('Ounces')),
        ('lb', _('Pounds')),
        ('cup', _('Cups')),
        ('tbsp', _('Tablespoons')),
        ('tsp', _('Teaspoons')),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    objects = InventoryItemQuerySet.as_manager()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    household = models.ForeignKey(
        'accounts.Household',
        on_delete=models.CASCADE,
        related_name='inventory_items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='inventory_items'
    )
    
    # Quantity and location
    current_quantity = models.DecimalField(
        _('current quantity'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    minimum_threshold = models.DecimalField(
        _('minimum threshold'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    unit = models.CharField(
        _('unit'),
        max_length=10,
        choices=QUANTITY_UNITS,
        default='count'
    )
    location = models.ForeignKey(
        StorageLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )
    
    # Dates
    purchase_date = models.DateField(
        _('purchase date'),
        default=timezone.now
    )
    expiration_date = models.DateField(
        _('expiration date'),
        null=True,
        blank=True
    )
    opened_date = models.DateField(
        _('opened date'),
        null=True,
        blank=True,
        help_text=_('Date when the item was opened')
    )
    
    # Additional info
    purchase_price = models.DecimalField(
        _('purchase price'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    notes = models.TextField(_('notes'), blank=True)
    
    # Status
    is_consumed = models.BooleanField(_('consumed'), default=False)
    consumed_date = models.DateTimeField(
        _('consumed date'),
        null=True,
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inventory_items'
        verbose_name = _('inventory item')
        verbose_name_plural = _('inventory items')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.current_quantity} {self.unit}"
    
    @property
    def is_expired(self):
        """Check if the item is expired."""
        if not self.expiration_date:
            return False
        return self.expiration_date < timezone.now().date()
    
    @property
    def days_until_expiration(self):
        """Calculate days until expiration."""
        if not self.expiration_date:
            return None
        delta = self.expiration_date - timezone.now().date()
        return delta.days
    
    @property
    def is_low_stock(self):
        """Check if the item is low on stock."""
        if self.minimum_threshold is None:
            return False
        return self.current_quantity < self.minimum_threshold
    
    @property
    def estimated_value(self):
        """Calculate estimated value based on purchase price and quantity."""
        if not self.purchase_price:
            return None
        return self.purchase_price * self.current_quantity
    
    def consume(self, amount):
        """Consume a specified amount from inventory."""
        if amount > self.current_quantity:
            raise ValueError("Cannot consume more than current quantity")
        self.current_quantity -= amount
        self.save()
    
    def add_stock(self, amount):
        """Add stock to inventory."""
        self.current_quantity += amount
        self.save()
    
    def clean(self):
        """Validate inventory item data."""
        from django.core.exceptions import ValidationError
        
        # Validate expiration date is after purchase date
        if (self.expiration_date and self.purchase_date and 
            self.expiration_date < self.purchase_date):
            raise ValidationError({
                'expiration_date': 'Expiration date cannot be before purchase date.'
            })
    
    def save(self, *args, **kwargs):
        # Auto-set household from user if not provided
        if not self.household_id and self.user.household_id:
            self.household_id = self.user.household_id
        
        # Mark as consumed if quantity is 0
        if self.current_quantity == 0 and not self.is_consumed:
            self.is_consumed = True
            self.consumed_date = timezone.now()
        
        super().save(*args, **kwargs)


class ProductBarcode(models.Model):
    """
    Additional barcodes for products (same product, different package sizes).
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='additional_barcodes'
    )
    barcode = models.CharField(
        _('barcode'),
        max_length=50,
        unique=True,
        db_index=True
    )
    barcode_type = models.CharField(
        _('barcode type'),
        max_length=20,
        choices=[
            ('EAN13', 'EAN-13'),
            ('UPC', 'UPC'),
            ('Code128', 'Code 128'),
            ('QR', 'QR Code'),
        ],
        default='EAN13'
    )
    package_size = models.CharField(
        _('package size'),
        max_length=50,
        blank=True,
        help_text=_('e.g., 500ml, 1kg')
    )
    is_verified = models.BooleanField(_('is verified'), default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'product_barcodes'
        verbose_name = _('product barcode')
        verbose_name_plural = _('product barcodes')
    
    def __str__(self):
        return f"{self.barcode} -> {self.product.name}"
    
    def clean(self):
        """Validate barcode format."""
        from django.core.exceptions import ValidationError
        
        if self.barcode_type == 'EAN13' and len(self.barcode) != 13:
            raise ValidationError({
                'barcode': f'EAN13 barcode must be exactly 13 digits, got {len(self.barcode)}'
            })
        elif self.barcode_type == 'UPC' and len(self.barcode) != 12:
            raise ValidationError({
                'barcode': f'UPC barcode must be exactly 12 digits, got {len(self.barcode)}'
            })

