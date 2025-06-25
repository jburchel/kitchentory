from rest_framework import serializers
from .models import Category, Product, StorageLocation, InventoryItem


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'color', 'icon', 'item_count']


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'brand', 'barcode', 'category', 'category_name',
            'default_unit', 'average_price', 'shelf_life_days', 
            'image_url', 'thumbnail_url', 'description'
        ]


class StorageLocationSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = StorageLocation
        fields = [
            'id', 'name', 'location_type', 'temperature', 
            'notes', 'item_count'
        ]


class InventoryItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)
    location = StorageLocationSerializer(read_only=True)
    location_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    
    # Computed fields
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiration = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    unit_display = serializers.CharField(source='get_unit_display', read_only=True)
    
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'product', 'product_id', 'location', 'location_id',
            'quantity', 'unit', 'unit_display', 'purchase_date', 'expiration_date',
            'price', 'notes', 'is_expired', 'days_until_expiration', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'household', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Set user and household from request context
        request = self.context['request']
        validated_data['user'] = request.user
        validated_data['household'] = request.user.household
        return super().create(validated_data)


class InventoryItemListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_brand = serializers.CharField(source='product.brand', read_only=True)
    product_thumbnail = serializers.URLField(source='product.thumbnail_url', read_only=True)
    category_name = serializers.CharField(source='product.category.name', read_only=True)
    category_color = serializers.CharField(source='product.category.color', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    # Computed fields
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiration = serializers.IntegerField(read_only=True)
    status = serializers.CharField(read_only=True)
    unit_display = serializers.CharField(source='get_unit_display', read_only=True)
    
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'product_name', 'product_brand', 'product_thumbnail',
            'category_name', 'category_color', 'location_name',
            'quantity', 'unit_display', 'expiration_date',
            'is_expired', 'days_until_expiration', 'status',
            'created_at', 'updated_at'
        ]


class QuickAddSerializer(serializers.Serializer):
    """Serializer for quick adding items by name"""
    name = serializers.CharField(max_length=200)
    brand = serializers.CharField(max_length=100, required=False, allow_blank=True)
    category_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.ChoiceField(choices=InventoryItem.QUANTITY_UNITS)
    location_id = serializers.UUIDField(required=False, allow_null=True)
    days_until_expiration = serializers.IntegerField(required=False, allow_null=True)
    
    def create(self, validated_data):
        from django.utils import timezone
        from datetime import timedelta
        
        request = self.context['request']
        
        # Create or get product
        product_data = {
            'name': validated_data['name'],
            'brand': validated_data.get('brand', ''),
            'category_id': validated_data['category_id'],
            'default_unit': validated_data['unit']
        }
        product, created = Product.objects.get_or_create(
            name=validated_data['name'],
            brand=validated_data.get('brand', ''),
            defaults=product_data
        )
        
        # Calculate expiration date
        expiration_date = None
        if validated_data.get('days_until_expiration'):
            expiration_date = timezone.now().date() + timedelta(
                days=validated_data['days_until_expiration']
            )
        
        # Create inventory item
        item_data = {
            'user': request.user,
            'household': request.user.household,
            'product': product,
            'quantity': validated_data['quantity'],
            'unit': validated_data['unit'],
            'location_id': validated_data.get('location_id'),
            'expiration_date': expiration_date,
            'purchase_date': timezone.now().date()
        }
        
        return InventoryItem.objects.create(**item_data)


class BulkActionSerializer(serializers.Serializer):
    """Serializer for bulk actions on inventory items"""
    item_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1
    )
    action = serializers.ChoiceField(choices=[
        ('consume', 'Mark as Consumed'),
        ('delete', 'Delete'),
        ('update_location', 'Update Location'),
        ('update_expiration', 'Update Expiration')
    ])
    
    # Optional fields for specific actions
    location_id = serializers.UUIDField(required=False, allow_null=True)
    expiration_date = serializers.DateField(required=False, allow_null=True)
    
    def validate(self, data):
        action = data['action']
        
        if action == 'update_location' and 'location_id' not in data:
            raise serializers.ValidationError({
                'location_id': 'Location ID is required for update_location action'
            })
        
        if action == 'update_expiration' and 'expiration_date' not in data:
            raise serializers.ValidationError({
                'expiration_date': 'Expiration date is required for update_expiration action'
            })
        
        return data