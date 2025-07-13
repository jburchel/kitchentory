"""
Integration tests for views across the application.
"""

import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from inventory.models import (
    Category,
    Product,
    ProductBarcode,
    StorageLocation,
    InventoryItem,
    Household,
)
from recipes.models import RecipeCategory, Recipe, RecipeIngredient, RecipeStep
from shopping.models import Store, ShoppingList, ShoppingListItem, ShoppingListShare

User = get_user_model()


class AuthenticationViewsTest(TestCase):
    """Test authentication-related views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_login_view_get(self):
        """Test login page loads correctly."""
        response = self.client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign In")

    def test_login_view_post_valid(self):
        """Test successful login."""
        response = self.client.post(
            reverse("account_login"), {"login": "testuser", "password": "testpass123"}
        )
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

    def test_login_view_post_invalid(self):
        """Test failed login."""
        response = self.client.post(
            reverse("account_login"), {"login": "testuser", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "incorrect")

    def test_logout_view(self):
        """Test logout functionality."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(reverse("account_logout"))
        self.assertEqual(response.status_code, 302)

    def test_signup_view_get(self):
        """Test signup page loads correctly."""
        response = self.client.get(reverse("account_signup"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign Up")

    def test_signup_view_post_valid(self):
        """Test successful signup."""
        response = self.client.post(
            reverse("account_signup"),
            {
                "username": "newuser",
                "email": "new@example.com",
                "password1": "complexpass123",
                "password2": "complexpass123",
            },
        )
        # Should redirect after successful signup
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())


class InventoryViewsTest(TestCase):
    """Test inventory-related views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.household.members.add(self.user)

        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product", category=self.category
        )
        self.location = StorageLocation.objects.create(
            name="Pantry", household=self.household
        )

        self.client.login(username="testuser", password="testpass123")

    def test_inventory_dashboard_view(self):
        """Test inventory dashboard loads correctly."""
        response = self.client.get(reverse("inventory:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inventory")

    def test_inventory_add_item_view_get(self):
        """Test add item form loads correctly."""
        response = self.client.get(reverse("inventory:add_item"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add Item")

    def test_inventory_add_item_view_post(self):
        """Test adding inventory item via form."""
        response = self.client.post(
            reverse("inventory:add_item"),
            {
                "product": self.product.id,
                "location": self.location.id,
                "current_quantity": "5.0",
                "unit": "pieces",
                "purchase_date": date.today().isoformat(),
                "expiration_date": (date.today() + timedelta(days=30)).isoformat(),
                "purchase_price": "9.99",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            InventoryItem.objects.filter(
                product=self.product, household=self.household
            ).exists()
        )

    def test_inventory_item_detail_view(self):
        """Test inventory item detail view."""
        item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("3.0"),
            unit="pieces",
        )

        response = self.client.get(
            reverse("inventory:item_detail", kwargs={"pk": item.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.product.name)

    def test_inventory_item_edit_view(self):
        """Test editing inventory item."""
        item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("3.0"),
            unit="pieces",
        )

        response = self.client.post(
            reverse("inventory:item_edit", kwargs={"pk": item.pk}),
            {
                "product": self.product.id,
                "location": self.location.id,
                "current_quantity": "7.0",
                "unit": "pieces",
                "purchase_date": date.today().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.current_quantity, Decimal("7.0"))

    def test_inventory_item_delete_view(self):
        """Test deleting inventory item."""
        item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal("3.0"),
            unit="pieces",
        )

        response = self.client.post(
            reverse("inventory:item_delete", kwargs={"pk": item.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(InventoryItem.objects.filter(pk=item.pk).exists())

    def test_barcode_scan_view(self):
        """Test barcode scanning view."""
        response = self.client.get(reverse("inventory:scan"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Scan Barcode")

    def test_barcode_lookup_view(self):
        """Test barcode lookup functionality."""
        ProductBarcode.objects.create(
            product=self.product, barcode="1234567890123", barcode_type="EAN13"
        )

        response = self.client.post(
            reverse("inventory:barcode_lookup"), {"barcode": "1234567890123"}
        )

        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data["product"]["name"], self.product.name)


class RecipeViewsTest(TestCase):
    """Test recipe-related views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testchef", email="chef@example.com", password="testpass123"
        )
        self.category = RecipeCategory.objects.create(name="Main Course")
        self.recipe = Recipe.objects.create(
            name="Test Recipe",
            description="A test recipe",
            category=self.category,
            created_by=self.user,
            servings=4,
            prep_time=15,
            cook_time=30,
            instructions="Cook and serve",
            is_public=True,
        )

        self.client.login(username="testchef", password="testpass123")

    def test_recipe_discovery_view(self):
        """Test recipe discovery page."""
        response = self.client.get(reverse("recipes:discovery"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recipe Discovery")

    def test_recipe_detail_view(self):
        """Test recipe detail view."""
        response = self.client.get(
            reverse("recipes:detail", kwargs={"slug": self.recipe.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.recipe.name)

    def test_recipe_create_view_get(self):
        """Test recipe creation form."""
        response = self.client.get(reverse("recipes:create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Recipe")

    def test_recipe_create_view_post(self):
        """Test creating a recipe."""
        response = self.client.post(
            reverse("recipes:create"),
            {
                "name": "New Recipe",
                "description": "A new recipe",
                "category": self.category.id,
                "servings": 2,
                "prep_time": 10,
                "cook_time": 20,
                "instructions": "Mix and cook",
                "difficulty": "easy",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Recipe.objects.filter(name="New Recipe", created_by=self.user).exists()
        )

    def test_recipe_edit_view(self):
        """Test editing a recipe."""
        response = self.client.post(
            reverse("recipes:edit", kwargs={"slug": self.recipe.slug}),
            {
                "name": "Updated Recipe",
                "description": self.recipe.description,
                "category": self.category.id,
                "servings": self.recipe.servings,
                "prep_time": self.recipe.prep_time,
                "cook_time": self.recipe.cook_time,
                "instructions": self.recipe.instructions,
                "difficulty": self.recipe.difficulty,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.name, "Updated Recipe")

    def test_recipe_delete_view(self):
        """Test deleting a recipe."""
        response = self.client.post(
            reverse("recipes:delete", kwargs={"slug": self.recipe.slug})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Recipe.objects.filter(slug=self.recipe.slug).exists())

    def test_recipe_cooking_mode_view(self):
        """Test cooking mode view."""
        response = self.client.get(
            reverse("recipes:cooking_mode", kwargs={"slug": self.recipe.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cooking Mode")


class ShoppingViewsTest(TestCase):
    """Test shopping-related views."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.household.members.add(self.user)

        self.store = Store.objects.create(name="Test Store", store_type="grocery")
        self.shopping_list = ShoppingList.objects.create(
            name="Test List",
            created_by=self.user,
            household=self.household,
            store=self.store,
        )

        self.client.login(username="testuser", password="testpass123")

    def test_shopping_dashboard_view(self):
        """Test shopping dashboard."""
        response = self.client.get(reverse("shopping:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Shopping Lists")

    def test_shopping_list_detail_view(self):
        """Test shopping list detail view."""
        response = self.client.get(
            reverse("shopping:list_detail", kwargs={"list_id": self.shopping_list.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.shopping_list.name)

    def test_shopping_list_create_view_get(self):
        """Test shopping list creation form."""
        response = self.client.get(reverse("shopping:create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Shopping List")

    def test_shopping_list_create_view_post(self):
        """Test creating a shopping list."""
        response = self.client.post(
            reverse("shopping:create"),
            {
                "name": "New Shopping List",
                "store": self.store.id,
                "budget_limit": "100.00",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ShoppingList.objects.filter(
                name="New Shopping List", created_by=self.user
            ).exists()
        )

    def test_shopping_list_edit_view(self):
        """Test editing a shopping list."""
        response = self.client.post(
            reverse("shopping:list_edit", kwargs={"list_id": self.shopping_list.id}),
            {"name": "Updated List", "store": self.store.id, "budget_limit": "150.00"},
        )

        self.assertEqual(response.status_code, 302)
        self.shopping_list.refresh_from_db()
        self.assertEqual(self.shopping_list.name, "Updated List")

    def test_add_item_to_shopping_list(self):
        """Test adding item to shopping list."""
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(name="Test Product", category=category)

        response = self.client.post(
            reverse("shopping:add_item", kwargs={"list_id": self.shopping_list.id}),
            {
                "product": product.id,
                "name": "Test Product",
                "quantity": "2.0",
                "unit": "pieces",
                "estimated_price": "5.99",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ShoppingListItem.objects.filter(
                shopping_list=self.shopping_list, product=product
            ).exists()
        )

    def test_shopping_list_sharing(self):
        """Test sharing a shopping list."""
        other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

        response = self.client.post(
            reverse("shopping:share_list", kwargs={"list_id": self.shopping_list.id}),
            {"email": other_user.email, "permission": "edit"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            ShoppingListShare.objects.filter(
                shopping_list=self.shopping_list, user=other_user
            ).exists()
        )


class AjaxViewsTest(TestCase):
    """Test AJAX endpoints."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )

        self.client.login(username="testuser", password="testpass123")

    def test_search_products_ajax(self):
        """Test product search AJAX endpoint."""
        category = Category.objects.create(name="Test Category")
        Product.objects.create(name="Apple", category=category)
        Product.objects.create(name="Banana", category=category)

        response = self.client.get(
            reverse("inventory:search_products"),
            {"q": "app"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("Apple", [p["name"] for p in data["products"]])

    def test_toggle_shopping_item_ajax(self):
        """Test toggling shopping list item status."""
        shopping_list = ShoppingList.objects.create(
            name="Test List", created_by=self.user, household=self.household
        )
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(name="Test Product", category=category)
        item = ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            product=product,
            name="Test Item",
            quantity=Decimal("1.0"),
        )

        response = self.client.post(
            reverse("shopping:toggle_item", kwargs={"item_id": item.id}),
            {"is_purchased": "true"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        item.refresh_from_db()
        self.assertTrue(item.is_purchased)


class FileUploadViewsTest(TestCase):
    """Test file upload functionality."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.category = RecipeCategory.objects.create(name="Main Course")

        self.client.login(username="testuser", password="testpass123")

    def test_recipe_image_upload(self):
        """Test uploading recipe image."""
        # Create a simple test image file
        image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01\x00\x00\x00\x00\x1e\xd6\xf1\xe2\x00\x00\x00\x00IEND\xaeB`\x82"
        uploaded_file = SimpleUploadedFile(
            "test_image.png", image_content, content_type="image/png"
        )

        response = self.client.post(
            reverse("recipes:create"),
            {
                "name": "Recipe with Image",
                "description": "A recipe with an image",
                "category": self.category.id,
                "servings": 4,
                "prep_time": 15,
                "cook_time": 30,
                "instructions": "Cook it",
                "difficulty": "easy",
                "image": uploaded_file,
            },
        )

        self.assertEqual(response.status_code, 302)
        recipe = Recipe.objects.get(name="Recipe with Image")
        self.assertIsNotNone(recipe.image)


class SecurityViewsTest(TestCase):
    """Test security-related view behaviors."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.other_user = User.objects.create_user(
            username="otheruser", email="other@example.com", password="testpass123"
        )

        self.household = Household.objects.create(
            name="Test Household", created_by=self.user
        )
        self.household.members.add(self.user)

        self.other_household = Household.objects.create(
            name="Other Household", created_by=self.other_user
        )
        self.other_household.members.add(self.other_user)

    def test_unauthorized_access_redirects_to_login(self):
        """Test that protected views redirect to login."""
        response = self.client.get(reverse("inventory:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_user_cannot_access_other_household_data(self):
        """Test that users cannot access other households' data."""
        # Create inventory item for other household
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(name="Test Product", category=category)
        location = StorageLocation.objects.create(
            name="Pantry", household=self.other_household
        )
        item = InventoryItem.objects.create(
            product=product,
            household=self.other_household,
            location=location,
            current_quantity=Decimal("1.0"),
        )

        # Login as first user and try to access other user's item
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(
            reverse("inventory:item_detail", kwargs={"pk": item.pk})
        )

        # Should return 404 or 403
        self.assertIn(response.status_code, [403, 404])

    def test_csrf_protection_on_forms(self):
        """Test CSRF protection on form submissions."""
        self.client.login(username="testuser", password="testpass123")

        # Get the form page first to get CSRF token
        response = self.client.get(reverse("inventory:add_item"))
        csrf_token = response.context["csrf_token"]

        # Submit without CSRF token should fail
        client_no_csrf = Client(enforce_csrf_checks=True)
        client_no_csrf.login(username="testuser", password="testpass123")

        response = client_no_csrf.post(
            reverse("inventory:add_item"), {"name": "Test Item"}
        )

        self.assertEqual(response.status_code, 403)

    def test_user_can_only_edit_own_recipes(self):
        """Test that users can only edit their own recipes."""
        category = RecipeCategory.objects.create(name="Main Course")
        recipe = Recipe.objects.create(
            name="Other User's Recipe", category=category, created_by=self.other_user
        )

        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(
            reverse("recipes:edit", kwargs={"slug": recipe.slug})
        )

        # Should return 404 or 403
        self.assertIn(response.status_code, [403, 404])
