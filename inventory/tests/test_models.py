"""
Unit tests for inventory models.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from inventory.models import (
    Category,
    Product,
    ProductBarcode,
    StorageLocation,
    InventoryItem,
)
from accounts.models import Household

User = get_user_model()


class CategoryModelTest(TestCase):
    """Test cases for Category model."""

    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category", description="A test category"
        )

    def test_category_creation(self):
        """Test basic category creation."""
        self.assertEqual(self.category.name, "Test Category")
        self.assertEqual(self.category.description, "A test category")
        self.assertIsNone(self.category.parent)
        self.assertEqual(str(self.category), "Test Category")

    def test_category_hierarchy(self):
        """Test category parent-child relationships."""
        child_category = Category.objects.create(
            name="Child Category", parent=self.category
        )

        self.assertEqual(child_category.parent, self.category)
        self.assertIn(child_category, self.category.children.all())

    def test_category_slug_generation(self):
        """Test automatic slug generation."""
        category = Category.objects.create(name="Test Category With Spaces")
        self.assertEqual(category.slug, "test-category-with-spaces")

    def test_category_unique_name_constraint(self):
        """Test that category names must be unique."""
        with self.assertRaises(IntegrityError):
            Category.objects.create(name="Test Category")


class ProductModelTest(TestCase):
    """Test cases for Product model."""

    def setUp(self):
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category,
            default_unit="pieces",
            description="A test product",
        )

    def test_product_creation(self):
        """Test basic product creation."""
        self.assertEqual(self.product.name, "Test Product")
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.default_unit, "pieces")
        self.assertEqual(str(self.product), "Test Product")

    def test_product_search_vector_update(self):
        """Test that search vector is updated on save."""
        # This would require PostgreSQL with full-text search
        # For now, just test that save works
        self.product.name = "Updated Product Name"
        self.product.save()
        self.assertEqual(self.product.name, "Updated Product Name")

    def test_product_average_price_calculation(self):
        """Test average price calculation."""
        # Initially no price
        self.assertIsNone(self.product.average_price)

        # Add some prices (this would be done through inventory items)
        # For now, just test the field exists
        self.product.average_price = Decimal("5.99")
        self.product.save()
        self.assertEqual(self.product.average_price, Decimal("5.99"))


class ProductBarcodeModelTest(TestCase):
    """Test cases for ProductBarcode model."""

    def setUp(self):
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category
        )
        self.barcode = ProductBarcode.objects.create(
            product=self.product, barcode="1234567890123", barcode_type="EAN13"
        )

    def test_barcode_creation(self):
        """Test basic barcode creation."""
        self.assertEqual(self.barcode.product, self.product)
        self.assertEqual(self.barcode.barcode, "1234567890123")
        self.assertEqual(self.barcode.barcode_type, "EAN13")
        self.assertTrue(self.barcode.is_verified)

    def test_barcode_validation(self):
        """Test barcode format validation."""
        # Test invalid EAN13 (too short)
        barcode = ProductBarcode(
            product=self.product, barcode="123456789", barcode_type="EAN13"
        )
        with self.assertRaises(ValidationError):
            barcode.full_clean()

    def test_barcode_uniqueness(self):
        """Test that barcodes must be unique."""
        with self.assertRaises(IntegrityError):
            ProductBarcode.objects.create(
                product=self.product, barcode="1234567890123", barcode_type="EAN13"
            )


class HouseholdModelTest(TestCase):
    """Test cases for Household model."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="testuser1", email="test1@example.com", password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user1
        )

    def test_household_creation(self):
        """Test basic household creation."""
        self.assertEqual(self.household.name, "Test Household")
        self.assertEqual(self.household.created_by, self.user1)
        self.assertEqual(str(self.household), "Test Household")

    def test_household_members(self):
        """Test adding members to household."""
        self.household.members.add(self.user1, self.user2)
        self.assertIn(self.user1, self.household.members.all())
        self.assertIn(self.user2, self.household.members.all())
        self.assertEqual(self.household.members.count(), 2)

    def test_household_invite_code_generation(self):
        """Test invite code generation."""
        # Should have an invite code after creation
        self.assertIsNotNone(self.household.invite_code)
        self.assertEqual(len(self.household.invite_code), 8)


class StorageLocationModelTest(TestCase):
    """Test cases for StorageLocation model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.location = StorageLocation.objects.create(
            name="Refrigerator", household=self.household, location_type="refrigerator"
        )

    def test_storage_location_creation(self):
        """Test basic storage location creation."""
        self.assertEqual(self.location.name, "Refrigerator")
        self.assertEqual(self.location.household, self.household)
        self.assertEqual(self.location.location_type, "refrigerator")
        self.assertEqual(str(self.location), "Refrigerator")

    def test_storage_location_temperature_validation(self):
        """Test temperature range validation."""
        # Test valid temperature
        self.location.temperature_min = 2.0
        self.location.temperature_max = 8.0
        self.location.full_clean()  # Should not raise

        # Test invalid range (min > max)
        self.location.temperature_min = 10.0
        self.location.temperature_max = 5.0
        with self.assertRaises(ValidationError):
            self.location.full_clean()


class InventoryItemModelTest(TestCase):
    """Test cases for InventoryItem model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category
        )
        self.location = StorageLocation.objects.create(
            name="Pantry", household=self.household
        )
        self.inventory_item = InventoryItem.objects.create(
            user=self.user,
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("5.0"),
            unit="count",
            purchase_date=date.today(),
            expiration_date=date.today() + timedelta(days=30),
        )

    def test_inventory_item_creation(self):
        """Test basic inventory item creation."""
        self.assertEqual(self.inventory_item.product, self.product)
        self.assertEqual(self.inventory_item.household, self.household)
        self.assertEqual(self.inventory_item.current_quantity, Decimal("5.0"))
        self.assertEqual(self.inventory_item.unit, "count")
        expected_str = f"Test Product - 5.0 count"
        self.assertEqual(str(self.inventory_item), expected_str)

    def test_inventory_item_quantity_validation(self):
        """Test quantity validation."""
        # Test negative quantity
        self.inventory_item.current_quantity = Decimal("-1.0")
        with self.assertRaises(ValidationError):
            self.inventory_item.full_clean()

        # Test zero quantity (should be valid)
        self.inventory_item.current_quantity = Decimal("0.0")
        self.inventory_item.full_clean()  # Should not raise

    def test_inventory_item_date_validation(self):
        """Test date validation."""
        # Test expiration before purchase
        self.inventory_item.purchase_date = date.today()
        self.inventory_item.expiration_date = date.today() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.inventory_item.full_clean()

    def test_inventory_item_is_expired_property(self):
        """Test is_expired property."""
        # Future expiration
        self.inventory_item.expiration_date = date.today() + timedelta(days=1)
        self.assertFalse(self.inventory_item.is_expired)

        # Past expiration
        self.inventory_item.expiration_date = date.today() - timedelta(days=1)
        self.assertTrue(self.inventory_item.is_expired)

        # No expiration date
        self.inventory_item.expiration_date = None
        self.assertFalse(self.inventory_item.is_expired)

    def test_inventory_item_days_until_expiration_property(self):
        """Test days_until_expiration property."""
        # Future expiration
        future_date = date.today() + timedelta(days=5)
        self.inventory_item.expiration_date = future_date
        self.assertEqual(self.inventory_item.days_until_expiration, 5)

        # Past expiration
        past_date = date.today() - timedelta(days=3)
        self.inventory_item.expiration_date = past_date
        self.assertEqual(self.inventory_item.days_until_expiration, -3)

        # No expiration date
        self.inventory_item.expiration_date = None
        self.assertIsNone(self.inventory_item.days_until_expiration)

    def test_inventory_item_is_low_stock_property(self):
        """Test is_low_stock property."""
        # Set minimum threshold
        self.inventory_item.minimum_threshold = Decimal("3.0")

        # Above threshold
        self.inventory_item.current_quantity = Decimal("5.0")
        self.assertFalse(self.inventory_item.is_low_stock)

        # Below threshold
        self.inventory_item.current_quantity = Decimal("2.0")
        self.assertTrue(self.inventory_item.is_low_stock)

        # At threshold
        self.inventory_item.current_quantity = Decimal("3.0")
        self.assertFalse(self.inventory_item.is_low_stock)

    def test_inventory_item_consume_method(self):
        """Test consume method."""
        initial_quantity = self.inventory_item.current_quantity

        # Valid consumption
        self.inventory_item.consume(Decimal("2.0"))
        self.assertEqual(
            self.inventory_item.current_quantity, initial_quantity - Decimal("2.0")
        )

        # Consumption exceeding current quantity
        with self.assertRaises(ValueError):
            self.inventory_item.consume(Decimal("10.0"))

    def test_inventory_item_add_stock_method(self):
        """Test add_stock method."""
        initial_quantity = self.inventory_item.current_quantity

        self.inventory_item.add_stock(Decimal("3.0"))
        self.assertEqual(
            self.inventory_item.current_quantity, initial_quantity + Decimal("3.0")
        )

    def test_inventory_item_estimated_value_calculation(self):
        """Test estimated value calculation."""
        self.inventory_item.purchase_price = Decimal("2.50")
        self.inventory_item.current_quantity = Decimal("4.0")

        # Calculate estimated value
        expected_value = Decimal("2.50") * Decimal("4.0")
        self.assertEqual(self.inventory_item.estimated_value, expected_value)

        # No purchase price
        self.inventory_item.purchase_price = None
        self.assertIsNone(self.inventory_item.estimated_value)


@pytest.mark.django_db
class InventoryItemQuerySetTest:
    """Test cases for InventoryItem QuerySet methods."""

    def setup_method(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category
        )
        self.location = StorageLocation.objects.create(
            name="Pantry", household=self.household
        )

    def test_expired_queryset_method(self):
        """Test expired() queryset method."""
        # Create expired item
        expired_item = InventoryItem.objects.create(
            user=self.user,
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("2.0"),
            expiration_date=date.today() - timedelta(days=1),
        )

        # Create non-expired item
        fresh_item = InventoryItem.objects.create(
            user=self.user,
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("3.0"),
            expiration_date=date.today() + timedelta(days=30),
        )

        expired_items = InventoryItem.objects.expired()
        assert expired_item in expired_items
        assert fresh_item not in expired_items

    def test_expiring_soon_queryset_method(self):
        """Test expiring_soon() queryset method."""
        # Create item expiring soon
        expiring_item = InventoryItem.objects.create(
            user=self.user,
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("2.0"),
            expiration_date=date.today() + timedelta(days=3),
        )

        # Create item expiring later
        fresh_item = InventoryItem.objects.create(
            user=self.user,
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("3.0"),
            expiration_date=date.today() + timedelta(days=30),
        )

        expiring_items = InventoryItem.objects.expiring_soon(days=7)
        assert expiring_item in expiring_items
        assert fresh_item not in expiring_items

    def test_low_stock_queryset_method(self):
        """Test low_stock() queryset method."""
        # Create low stock item
        low_stock_item = InventoryItem.objects.create(
            user=self.user,
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("1.0"),
            minimum_threshold=Decimal("3.0"),
        )

        # Create adequate stock item
        good_stock_item = InventoryItem.objects.create(
            user=self.user,
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("5.0"),
            minimum_threshold=Decimal("3.0"),
        )

        low_stock_items = InventoryItem.objects.low_stock()
        assert low_stock_item in low_stock_items
        assert good_stock_item not in low_stock_items
