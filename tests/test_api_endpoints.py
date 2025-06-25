"""
API endpoint tests for Kitchentory.
"""

import json
from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from inventory.models import (
    Category, Product, ProductBarcode, StorageLocation, 
    InventoryItem, Household
)
from recipes.models import (
    RecipeCategory, Recipe, RecipeIngredient, RecipeStep
)
from shopping.models import (
    Store, ShoppingList, ShoppingListItem
)

User = get_user_model()


class AuthenticationAPITest(APITestCase):
    """Test API authentication endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_obtain_auth_token(self):
        """Test obtaining authentication token."""
        url = reverse('api:auth:login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
    
    def test_invalid_credentials(self):
        """Test authentication with invalid credentials."""
        url = reverse('api:auth:login')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_token_required_for_protected_endpoints(self):
        """Test that protected endpoints require authentication."""
        url = reverse('api:inventory:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class InventoryAPITest(APITestCase):
    """Test inventory API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        self.household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
        self.household.members.add(self.user)
        
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category
        )
        self.location = StorageLocation.objects.create(
            name="Pantry",
            household=self.household
        )
    
    def test_get_inventory_list(self):
        """Test retrieving inventory list."""
        # Create inventory items
        InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal('5.0'),
            unit='pieces'
        )
        
        url = reverse('api:inventory:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['product']['name'], 'Test Product')
    
    def test_create_inventory_item(self):
        """Test creating inventory item via API."""
        url = reverse('api:inventory:list')
        data = {
            'product': self.product.id,
            'location': self.location.id,
            'current_quantity': '3.0',
            'unit': 'pieces',
            'purchase_date': date.today().isoformat(),
            'expiration_date': (date.today() + timedelta(days=30)).isoformat(),
            'purchase_price': '4.99'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            InventoryItem.objects.filter(
                product=self.product,
                household=self.household
            ).exists()
        )
    
    def test_update_inventory_item(self):
        """Test updating inventory item via API."""
        item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal('5.0'),
            unit='pieces'
        )
        
        url = reverse('api:inventory:detail', kwargs={'pk': item.pk})
        data = {
            'product': self.product.id,
            'location': self.location.id,
            'current_quantity': '8.0',
            'unit': 'pieces'
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertEqual(item.current_quantity, Decimal('8.0'))
    
    def test_delete_inventory_item(self):
        """Test deleting inventory item via API."""
        item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal('5.0'),
            unit='pieces'
        )
        
        url = reverse('api:inventory:detail', kwargs={'pk': item.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            InventoryItem.objects.filter(pk=item.pk).exists()
        )
    
    def test_inventory_filtering(self):
        """Test filtering inventory by various criteria."""
        # Create items with different characteristics
        expired_item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal('2.0'),
            unit='pieces',
            expiration_date=date.today() - timedelta(days=1)
        )
        
        fresh_item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal('3.0'),
            unit='pieces',
            expiration_date=date.today() + timedelta(days=30)
        )
        
        # Test expired filter
        url = reverse('api:inventory:list')
        response = self.client.get(url, {'expired': 'true'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item_ids = [item['id'] for item in response.data['results']]
        self.assertIn(expired_item.id, item_ids)
        self.assertNotIn(fresh_item.id, item_ids)
    
    def test_search_products(self):
        """Test product search endpoint."""
        url = reverse('api:inventory:search_products')
        response = self.client.get(url, {'q': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Product')
    
    def test_barcode_lookup(self):
        """Test barcode lookup endpoint."""
        ProductBarcode.objects.create(
            product=self.product,
            barcode="1234567890123",
            barcode_type="EAN13"
        )
        
        url = reverse('api:inventory:barcode_lookup')
        response = self.client.get(url, {'barcode': '1234567890123'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['product']['name'], 'Test Product')
    
    def test_inventory_statistics(self):
        """Test inventory statistics endpoint."""
        # Create various inventory items
        InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal('5.0'),
            unit='pieces',
            purchase_price=Decimal('10.00')
        )
        
        url = reverse('api:inventory:statistics')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_items', response.data)
        self.assertIn('total_value', response.data)
        self.assertIn('expiring_soon', response.data)


class RecipeAPITest(APITestCase):
    """Test recipe API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testchef",
            email="chef@example.com",
            password="testpass123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
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
            is_public=True
        )
    
    def test_get_recipe_list(self):
        """Test retrieving recipe list."""
        url = reverse('api:recipes:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Recipe')
    
    def test_create_recipe(self):
        """Test creating recipe via API."""
        url = reverse('api:recipes:list')
        data = {
            'name': 'New Recipe',
            'description': 'A new recipe',
            'category': self.category.id,
            'servings': 2,
            'prep_time': 10,
            'cook_time': 20,
            'instructions': 'Mix and cook',
            'difficulty': 'easy'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Recipe.objects.filter(name='New Recipe', created_by=self.user).exists()
        )
    
    def test_update_recipe(self):
        """Test updating recipe via API."""
        url = reverse('api:recipes:detail', kwargs={'pk': self.recipe.pk})
        data = {
            'name': 'Updated Recipe',
            'description': self.recipe.description,
            'category': self.category.id,
            'servings': 6,
            'prep_time': self.recipe.prep_time,
            'cook_time': self.recipe.cook_time,
            'instructions': self.recipe.instructions,
            'difficulty': self.recipe.difficulty
        }
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.name, 'Updated Recipe')
        self.assertEqual(self.recipe.servings, 6)
    
    def test_recipe_ingredients_endpoint(self):
        """Test recipe ingredients sub-endpoint."""
        product_category = Category.objects.create(name="Vegetables")
        product = Product.objects.create(
            name="Tomato",
            category=product_category
        )
        
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            product=product,
            quantity=Decimal('2.0'),
            unit='pieces'
        )
        
        url = reverse('api:recipes:ingredients', kwargs={'pk': self.recipe.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['product']['name'], 'Tomato')
    
    def test_recipe_matching_endpoint(self):
        """Test recipe matching based on available ingredients."""
        household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
        location = StorageLocation.objects.create(
            name="Pantry",
            household=household
        )
        product_category = Category.objects.create(name="Vegetables")
        product = Product.objects.create(
            name="Tomato",
            category=product_category
        )
        
        # Add ingredient to recipe
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            product=product,
            quantity=Decimal('2.0'),
            unit='pieces'
        )
        
        # Add to inventory
        InventoryItem.objects.create(
            product=product,
            household=household,
            location=location,
            current_quantity=Decimal('5.0'),
            unit='pieces'
        )
        
        url = reverse('api:recipes:matching')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        recipe_names = [recipe['name'] for recipe in response.data['results']]
        self.assertIn('Test Recipe', recipe_names)
    
    def test_recipe_search(self):
        """Test recipe search endpoint."""
        url = reverse('api:recipes:search')
        response = self.client.get(url, {'q': 'Test'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test Recipe')


class ShoppingAPITest(APITestCase):
    """Test shopping API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        self.household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
        self.household.members.add(self.user)
        
        self.store = Store.objects.create(
            name="Test Store",
            store_type="grocery"
        )
        self.shopping_list = ShoppingList.objects.create(
            name="Test List",
            created_by=self.user,
            household=self.household,
            store=self.store
        )
    
    def test_get_shopping_lists(self):
        """Test retrieving shopping lists."""
        url = reverse('api:shopping:lists')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['name'], 'Test List')
    
    def test_create_shopping_list(self):
        """Test creating shopping list via API."""
        url = reverse('api:shopping:lists')
        data = {
            'name': 'New Shopping List',
            'store': self.store.id,
            'budget_limit': '100.00'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            ShoppingList.objects.filter(
                name='New Shopping List',
                created_by=self.user
            ).exists()
        )
    
    def test_add_item_to_list(self):
        """Test adding item to shopping list."""
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(
            name="Test Product",
            category=category
        )
        
        url = reverse('api:shopping:items', kwargs={'list_id': self.shopping_list.id})
        data = {
            'product': product.id,
            'name': 'Test Product',
            'quantity': '2.0',
            'unit': 'pieces',
            'estimated_price': '5.99'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            ShoppingListItem.objects.filter(
                shopping_list=self.shopping_list,
                product=product
            ).exists()
        )
    
    def test_toggle_item_purchased(self):
        """Test toggling item purchased status."""
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(
            name="Test Product",
            category=category
        )
        item = ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            product=product,
            name="Test Item",
            quantity=Decimal('1.0')
        )
        
        url = reverse('api:shopping:toggle_item', kwargs={'item_id': item.id})
        data = {'is_purchased': True}
        
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item.refresh_from_db()
        self.assertTrue(item.is_purchased)
    
    def test_generate_list_from_depleted_items(self):
        """Test generating shopping list from depleted inventory."""
        # Create inventory setup
        location = StorageLocation.objects.create(
            name="Pantry",
            household=self.household
        )
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(
            name="Low Stock Product",
            category=category
        )
        
        # Create low stock item
        InventoryItem.objects.create(
            product=product,
            household=self.household,
            location=location,
            current_quantity=Decimal('1.0'),
            minimum_threshold=Decimal('5.0'),
            unit='pieces'
        )
        
        url = reverse('api:shopping:generate_from_depleted')
        data = {
            'name': 'Restock List',
            'threshold_days': 7
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that list was created with the low stock item
        new_list = ShoppingList.objects.get(name='Restock List')
        self.assertTrue(
            new_list.items.filter(product=product).exists()
        )


class ValidationAPITest(APITestCase):
    """Test API validation and error handling."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        self.household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
    
    def test_invalid_data_returns_400(self):
        """Test that invalid data returns 400 Bad Request."""
        url = reverse('api:inventory:list')
        data = {
            'current_quantity': 'invalid_number',
            'unit': ''  # Required field
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_quantity', response.data)
    
    def test_unauthorized_access_returns_401(self):
        """Test that unauthorized access returns 401."""
        self.client.credentials()  # Remove authentication
        
        url = reverse('api:inventory:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_accessing_nonexistent_resource_returns_404(self):
        """Test that accessing non-existent resource returns 404."""
        url = reverse('api:inventory:detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_method_not_allowed_returns_405(self):
        """Test that unsupported methods return 405."""
        url = reverse('api:inventory:list')
        response = self.client.put(url, {}, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)


class PaginationAPITest(APITestCase):
    """Test API pagination."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        self.household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
        self.household.members.add(self.user)
        
        # Create many items for pagination testing
        self.category = Category.objects.create(name="Test Category")
        self.location = StorageLocation.objects.create(
            name="Pantry",
            household=self.household
        )
        
        for i in range(25):  # Create more than default page size
            product = Product.objects.create(
                name=f"Product {i}",
                category=self.category
            )
            InventoryItem.objects.create(
                product=product,
                household=self.household,
                location=self.location,
                current_quantity=Decimal('1.0'),
                unit='pieces'
            )
    
    def test_pagination_metadata(self):
        """Test that pagination metadata is included."""
        url = reverse('api:inventory:list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)
    
    def test_page_size_parameter(self):
        """Test custom page size parameter."""
        url = reverse('api:inventory:list')
        response = self.client.get(url, {'page_size': 5})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)
    
    def test_next_page_link(self):
        """Test navigation to next page."""
        url = reverse('api:inventory:list')
        response = self.client.get(url, {'page_size': 10})
        
        self.assertIsNotNone(response.data['next'])
        
        # Follow next page link
        next_response = self.client.get(response.data['next'])
        self.assertEqual(next_response.status_code, status.HTTP_200_OK)


class RateLimitingAPITest(APITestCase):
    """Test API rate limiting (if implemented)."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
    
    def test_rate_limiting_headers(self):
        """Test that rate limiting headers are present (if implemented)."""
        url = reverse('api:inventory:list')
        response = self.client.get(url)
        
        # These headers would be added by rate limiting middleware
        # For now, just test that the endpoint works
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # If rate limiting is implemented, test headers like:
        # self.assertIn('X-RateLimit-Limit', response)
        # self.assertIn('X-RateLimit-Remaining', response)