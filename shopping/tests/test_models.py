"""
Unit tests for shopping models.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from shopping.models import (
    Store,
    ShoppingList,
    ShoppingListItem,
    ShoppingListShare,
    RecurringShoppingItem,
)
from inventory.models import Category, Product
from accounts.models import Household

User = get_user_model()


class StoreModelTest(TestCase):
    """Test cases for Store model."""

    def setUp(self):
        self.store = Store.objects.create(
            name="Test Grocery Store",
            address="123 Main St, Test City",
            store_type="grocery",
        )

    def test_store_creation(self):
        """Test basic store creation."""
        self.assertEqual(self.store.name, "Test Grocery Store")
        self.assertEqual(self.store.address, "123 Main St, Test City")
        self.assertEqual(self.store.store_type, "grocery")
        self.assertEqual(str(self.store), "Test Grocery Store")

    def test_store_slug_generation(self):
        """Test automatic slug generation."""
        store = Store.objects.create(name="Super Market & More!", store_type="grocery")
        self.assertEqual(store.slug, "super-market-more")

    def test_store_unique_name_constraint(self):
        """Test that store names must be unique."""
        with self.assertRaises(IntegrityError):
            Store.objects.create(name="Test Grocery Store", store_type="grocery")


class ShoppingListModelTest(TestCase):
    """Test cases for ShoppingList model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.store = Store.objects.create(name="Test Store", store_type="grocery")
        self.shopping_list = ShoppingList.objects.create(
            name="Weekly Groceries",
            created_by=self.user,
            household=self.household,
            store=self.store,
        )

    def test_shopping_list_creation(self):
        """Test basic shopping list creation."""
        self.assertEqual(self.shopping_list.name, "Weekly Groceries")
        self.assertEqual(self.shopping_list.created_by, self.user)
        self.assertEqual(self.shopping_list.household, self.household)
        self.assertEqual(self.shopping_list.store, self.store)
        self.assertEqual(self.shopping_list.status, "active")
        self.assertEqual(str(self.shopping_list), "Weekly Groceries")

    def test_shopping_list_status_choices(self):
        """Test shopping list status validation."""
        # Test valid status
        self.shopping_list.status = "shopping"
        self.shopping_list.full_clean()  # Should not raise

        # Test invalid status
        self.shopping_list.status = "invalid_status"
        with self.assertRaises(ValidationError):
            self.shopping_list.full_clean()

    def test_shopping_list_budget_validation(self):
        """Test budget limit validation."""
        # Test negative budget
        self.shopping_list.budget_limit = Decimal("-10.00")
        with self.assertRaises(ValidationError):
            self.shopping_list.full_clean()

        # Test valid budget
        self.shopping_list.budget_limit = Decimal("100.00")
        self.shopping_list.full_clean()  # Should not raise

    def test_shopping_list_total_items_property(self):
        """Test total_items property."""
        # Initially no items
        self.assertEqual(self.shopping_list.total_items, 0)

        # Add items (this would be tested with ShoppingListItem)
        # For now, just test the property exists
        self.assertIsInstance(self.shopping_list.total_items, int)

    def test_shopping_list_completed_items_property(self):
        """Test completed_items property."""
        # Initially no completed items
        self.assertEqual(self.shopping_list.completed_items, 0)

        # Test property exists
        self.assertIsInstance(self.shopping_list.completed_items, int)

    def test_shopping_list_completion_percentage_property(self):
        """Test completion_percentage property."""
        # With no items, should be 0
        self.assertEqual(self.shopping_list.completion_percentage, 0)

    def test_shopping_list_estimated_total_property(self):
        """Test estimated_total property."""
        # Initially zero
        self.assertEqual(self.shopping_list.estimated_total, Decimal("0.00"))


class ShoppingListItemModelTest(TestCase):
    """Test cases for ShoppingListItem model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.shopping_list = ShoppingList.objects.create(
            name="Test List", created_by=self.user, household=self.household
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category
        )
        self.shopping_item = ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            product=self.product,
            name="Test Product",
            quantity=Decimal("2.0"),
            unit="pieces",
            estimated_price=Decimal("5.99"),
        )

    def test_shopping_list_item_creation(self):
        """Test basic shopping list item creation."""
        self.assertEqual(self.shopping_item.shopping_list, self.shopping_list)
        self.assertEqual(self.shopping_item.product, self.product)
        self.assertEqual(self.shopping_item.name, "Test Product")
        self.assertEqual(self.shopping_item.quantity, Decimal("2.0"))
        self.assertEqual(self.shopping_item.unit, "pieces")
        self.assertEqual(self.shopping_item.estimated_price, Decimal("5.99"))
        self.assertFalse(self.shopping_item.is_purchased)
        expected_str = "Test Product - 2.0 pieces"
        self.assertEqual(str(self.shopping_item), expected_str)

    def test_shopping_list_item_validation(self):
        """Test shopping list item validation."""
        # Test negative quantity
        self.shopping_item.quantity = Decimal("-1.0")
        with self.assertRaises(ValidationError):
            self.shopping_item.full_clean()

        # Test negative price
        self.shopping_item.quantity = Decimal("2.0")  # Reset
        self.shopping_item.estimated_price = Decimal("-1.00")
        with self.assertRaises(ValidationError):
            self.shopping_item.full_clean()

    def test_shopping_list_item_priority_choices(self):
        """Test item priority validation."""
        # Test valid priority
        self.shopping_item.priority = "high"
        self.shopping_item.full_clean()  # Should not raise

        # Test invalid priority
        self.shopping_item.priority = "invalid_priority"
        with self.assertRaises(ValidationError):
            self.shopping_item.full_clean()

    def test_shopping_list_item_ordering(self):
        """Test custom ordering functionality."""
        item2 = ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            product=self.product,
            name="Second Item",
            quantity=Decimal("1.0"),
            custom_order=2,
        )

        items = self.shopping_list.items.all()
        self.assertEqual(items[0], self.shopping_item)  # custom_order=1 by default
        self.assertEqual(items[1], item2)  # custom_order=2

    def test_shopping_list_item_mark_purchased(self):
        """Test marking item as purchased."""
        self.assertFalse(self.shopping_item.is_purchased)
        self.assertIsNone(self.shopping_item.purchased_at)

        self.shopping_item.mark_purchased()

        self.assertTrue(self.shopping_item.is_purchased)
        self.assertIsNotNone(self.shopping_item.purchased_at)

    def test_shopping_list_item_mark_unpurchased(self):
        """Test marking item as unpurchased."""
        # First mark as purchased
        self.shopping_item.mark_purchased()
        self.assertTrue(self.shopping_item.is_purchased)

        # Then mark as unpurchased
        self.shopping_item.mark_unpurchased()

        self.assertFalse(self.shopping_item.is_purchased)
        self.assertIsNone(self.shopping_item.purchased_at)

    def test_shopping_list_item_total_cost_property(self):
        """Test total_cost property calculation."""
        expected_cost = self.shopping_item.quantity * self.shopping_item.estimated_price
        self.assertEqual(self.shopping_item.total_cost, expected_cost)

        # Test with no estimated price
        self.shopping_item.estimated_price = None
        self.assertIsNone(self.shopping_item.total_cost)


class ShoppingListShareModelTest(TestCase):
    """Test cases for ShoppingListShare model."""

    def setUp(self):
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="testpass123"
        )
        self.shared_user = User.objects.create_user(
            username="shared", email="shared@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.owner
        )
        self.shopping_list = ShoppingList.objects.create(
            name="Shared List", created_by=self.owner, household=self.household
        )
        self.share = ShoppingListShare.objects.create(
            shopping_list=self.shopping_list,
            user=self.shared_user,
            permission="edit",
            shared_by=self.owner,
        )

    def test_shopping_list_share_creation(self):
        """Test basic share creation."""
        self.assertEqual(self.share.shopping_list, self.shopping_list)
        self.assertEqual(self.share.user, self.shared_user)
        self.assertEqual(self.share.permission, "edit")
        expected_str = f"Shared List shared with {self.shared_user.username}"
        self.assertEqual(str(self.share), expected_str)

    def test_shopping_list_share_permission_choices(self):
        """Test permission validation."""
        # Test valid permission
        self.share.permission = "view"
        self.share.full_clean()  # Should not raise

        # Test invalid permission
        self.share.permission = "invalid_permission"
        with self.assertRaises(ValidationError):
            self.share.full_clean()

    def test_shopping_list_share_unique_constraint(self):
        """Test that user-list combinations must be unique."""
        with self.assertRaises(IntegrityError):
            ShoppingListShare.objects.create(
                shopping_list=self.shopping_list,
                user=self.shared_user,
                permission="view",
                shared_by=self.owner,
            )

    def test_shopping_list_share_can_edit_property(self):
        """Test can_edit property."""
        # Edit permission should allow editing
        self.share.permission = "edit"
        self.assertTrue(self.share.can_edit)

        # View permission should not allow editing
        self.share.permission = "view"
        self.assertFalse(self.share.can_edit)


class RecurringShoppingItemModelTest(TestCase):
    """Test cases for RecurringShoppingItem model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(name="Milk", category=self.category)
        self.recurring_item = RecurringShoppingItem.objects.create(
            user=self.user,
            household=self.household,
            product=self.product,
            name="Milk",
            quantity=Decimal("1.0"),
            unit="gallon",
            frequency="weekly",
        )

    def test_recurring_shopping_item_creation(self):
        """Test basic recurring item creation."""
        self.assertEqual(self.recurring_item.household, self.household)
        self.assertEqual(self.recurring_item.product, self.product)
        self.assertEqual(self.recurring_item.name, "Milk")
        self.assertEqual(self.recurring_item.quantity, Decimal("1.0"))
        self.assertEqual(self.recurring_item.unit, "gallon")
        self.assertEqual(self.recurring_item.frequency, "weekly")
        self.assertTrue(self.recurring_item.is_active)
        expected_str = "Milk - 1.0 gallon (weekly)"
        self.assertEqual(str(self.recurring_item), expected_str)

    def test_recurring_item_frequency_choices(self):
        """Test frequency validation."""
        # Test valid frequency
        self.recurring_item.frequency = "monthly"
        self.recurring_item.full_clean()  # Should not raise

        # Test invalid frequency
        self.recurring_item.frequency = "invalid_frequency"
        with self.assertRaises(ValidationError):
            self.recurring_item.full_clean()

    def test_recurring_item_next_due_date_calculation(self):
        """Test next_due_date calculation."""
        # Set last added date
        self.recurring_item.last_added_date = date.today() - timedelta(days=5)

        # Weekly frequency should be due in 2 days
        expected_date = date.today() + timedelta(days=2)
        self.assertEqual(self.recurring_item.next_due_date, expected_date)

    def test_recurring_item_is_due_property(self):
        """Test is_due property."""
        # Set last added date to a week ago for weekly item
        self.recurring_item.last_added_date = date.today() - timedelta(days=7)
        self.assertTrue(self.recurring_item.is_due)

        # Set last added date to yesterday
        self.recurring_item.last_added_date = date.today() - timedelta(days=1)
        self.assertFalse(self.recurring_item.is_due)

    def test_recurring_item_mark_added(self):
        """Test marking item as added to a list."""
        old_date = self.recurring_item.last_added_date

        self.recurring_item.mark_added()

        self.assertNotEqual(self.recurring_item.last_added_date, old_date)
        self.assertEqual(self.recurring_item.last_added_date, date.today())


@pytest.mark.django_db
class ShoppingListQuerySetTest:
    """Test cases for ShoppingList QuerySet methods."""

    def setup_method(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )

        # Create active list
        self.active_list = ShoppingList.objects.create(
            name="Active List",
            created_by=self.user,
            household=self.household,
            status="active",
        )

        # Create completed list
        self.completed_list = ShoppingList.objects.create(
            name="Completed List",
            created_by=self.user,
            household=self.household,
            status="completed",
        )

        # Create shopping list
        self.shopping_list = ShoppingList.objects.create(
            name="Shopping List",
            created_by=self.user,
            household=self.household,
            status="shopping",
        )

    def test_active_queryset_method(self):
        """Test active() queryset method."""
        active_lists = ShoppingList.objects.active()
        assert self.active_list in active_lists
        assert self.shopping_list in active_lists
        assert self.completed_list not in active_lists

    def test_for_household_queryset_method(self):
        """Test for_household() queryset method."""
        household_lists = ShoppingList.objects.for_household(self.household)
        assert self.active_list in household_lists
        assert self.completed_list in household_lists
        assert self.shopping_list in household_lists

        # Test with different household
        other_user = User.objects.create_user(
            username="other", email="other@example.com", password="testpass123"
        )
        other_household = Household.objects.create(
            name="Other Household", created_by=other_user
        )
        other_lists = ShoppingList.objects.for_household(other_household)
        assert self.active_list not in other_lists

    def test_shared_with_user_queryset_method(self):
        """Test shared_with_user() queryset method."""
        # Create another user and share a list
        other_user = User.objects.create_user(
            username="shared_user", email="shared@example.com", password="testpass123"
        )

        ShoppingListShare.objects.create(
            shopping_list=self.active_list,
            user=other_user,
            permission="view",
            shared_by=self.user,
        )

        shared_lists = ShoppingList.objects.shared_with_user(other_user)
        assert self.active_list in shared_lists
        assert self.completed_list not in shared_lists


@pytest.mark.django_db
class ShoppingListItemQuerySetTest:
    """Test cases for ShoppingListItem QuerySet methods."""

    def setup_method(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.shopping_list = ShoppingList.objects.create(
            name="Test List", created_by=self.user, household=self.household
        )
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category
        )

        # Create purchased item
        self.purchased_item = ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            product=self.product,
            name="Purchased Item",
            quantity=Decimal("1.0"),
            is_purchased=True,
        )

        # Create unpurchased item
        self.unpurchased_item = ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            product=self.product,
            name="Unpurchased Item",
            quantity=Decimal("2.0"),
            is_purchased=False,
        )

    def test_purchased_queryset_method(self):
        """Test purchased() queryset method."""
        purchased_items = ShoppingListItem.objects.purchased()
        assert self.purchased_item in purchased_items
        assert self.unpurchased_item not in purchased_items

    def test_pending_queryset_method(self):
        """Test pending() queryset method."""
        pending_items = ShoppingListItem.objects.pending()
        assert self.unpurchased_item in pending_items
        assert self.purchased_item not in pending_items

    def test_by_priority_queryset_method(self):
        """Test by_priority() queryset method."""
        # Set priorities
        self.purchased_item.priority = "high"
        self.purchased_item.save()
        self.unpurchased_item.priority = "normal"
        self.unpurchased_item.save()

        high_priority_items = ShoppingListItem.objects.by_priority("high")
        assert self.purchased_item in high_priority_items
        assert self.unpurchased_item not in high_priority_items
