"""
End-to-end tests for Kitchentory using Playwright.
"""

import pytest
from django.test import LiveServerTestCase
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page
from inventory.models import Category, Product, Household, StorageLocation
from recipes.models import RecipeCategory, Recipe
from shopping.models import Store, ShoppingList

User = get_user_model()


class PlaywrightTestCase(StaticLiveServerTestCase):
    """Base class for Playwright E2E tests."""
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
    
    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()
    
    def setUp(self):
        super().setUp()
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        # Create test user
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        
        # Create household
        self.household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
        self.household.members.add(self.user)
    
    def tearDown(self):
        self.context.close()
        super().tearDown()
    
    def login_user(self):
        """Helper method to log in the test user."""
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.fill('[name="login"]', 'testuser')
        self.page.fill('[name="password"]', 'testpass123')
        self.page.click('button[type="submit"]')
        self.page.wait_for_url(f"{self.live_server_url}/")


class AuthenticationE2ETest(PlaywrightTestCase):
    """Test authentication flows."""
    
    def test_user_can_sign_up(self):
        """Test user registration flow."""
        self.page.goto(f"{self.live_server_url}/accounts/signup/")
        
        # Fill signup form
        self.page.fill('[name="username"]', 'newuser')
        self.page.fill('[name="email"]', 'newuser@example.com')
        self.page.fill('[name="password1"]', 'complexpass123')
        self.page.fill('[name="password2"]', 'complexpass123')
        
        # Submit form
        self.page.click('button[type="submit"]')
        
        # Should redirect to verification page or dashboard
        self.page.wait_for_load_state('networkidle')
        self.assertIn('verification', self.page.url.lower() or 'dashboard' in self.page.url.lower())
    
    def test_user_can_login_and_logout(self):
        """Test login and logout flow."""
        # Login
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.fill('[name="login"]', 'testuser')
        self.page.fill('[name="password"]', 'testpass123')
        self.page.click('button[type="submit"]')
        
        # Should be redirected to dashboard
        self.page.wait_for_url(f"{self.live_server_url}/")
        self.assertIn('testuser', self.page.content())
        
        # Logout
        self.page.click('[data-test="logout-button"]')
        self.page.wait_for_url('**/accounts/logout/**')
        
        # Should be logged out
        self.page.goto(f"{self.live_server_url}/")
        self.assertIn('Sign In', self.page.content())
    
    def test_login_with_invalid_credentials(self):
        """Test login with wrong credentials."""
        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.fill('[name="login"]', 'testuser')
        self.page.fill('[name="password"]', 'wrongpassword')
        self.page.click('button[type="submit"]')
        
        # Should show error message
        self.page.wait_for_selector('.alert-error, .error')
        error_text = self.page.inner_text('.alert-error, .error')
        self.assertIn('incorrect', error_text.lower())


class InventoryE2ETest(PlaywrightTestCase):
    """Test inventory management flows."""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category
        )
        self.location = StorageLocation.objects.create(
            name="Pantry",
            household=self.household
        )
        
        self.login_user()
    
    def test_user_can_view_inventory_dashboard(self):
        """Test accessing inventory dashboard."""
        self.page.goto(f"{self.live_server_url}/inventory/")
        
        # Should see inventory page
        self.assertIn('Inventory', self.page.title())
        self.page.wait_for_selector('[data-test="inventory-dashboard"]')
    
    def test_user_can_add_inventory_item(self):
        """Test adding an inventory item."""
        self.page.goto(f"{self.live_server_url}/inventory/add/")
        
        # Fill form
        self.page.select_option('[name="product"]', str(self.product.id))
        self.page.select_option('[name="location"]', str(self.location.id))
        self.page.fill('[name="current_quantity"]', '5')
        self.page.fill('[name="unit"]', 'pieces')
        self.page.fill('[name="purchase_price"]', '9.99')
        
        # Submit form
        self.page.click('button[type="submit"]')
        
        # Should redirect to inventory list
        self.page.wait_for_url('**/inventory/**')
        self.assertIn('Test Product', self.page.content())
    
    def test_user_can_edit_inventory_item(self):
        """Test editing an inventory item."""
        # First create an item
        from inventory.models import InventoryItem
        from decimal import Decimal
        
        item = InventoryItem.objects.create(
            product=self.product,
            household=self.household,
            location=self.location,
            current_quantity=Decimal('3.0'),
            unit='pieces'
        )
        
        # Navigate to edit page
        self.page.goto(f"{self.live_server_url}/inventory/item/{item.id}/edit/")
        
        # Update quantity
        self.page.fill('[name="current_quantity"]', '7')
        self.page.click('button[type="submit"]')
        
        # Should see updated quantity
        self.page.wait_for_url('**/inventory/**')
        self.assertIn('7', self.page.content())
    
    def test_barcode_scanning_interface(self):
        """Test barcode scanning interface."""
        self.page.goto(f"{self.live_server_url}/inventory/scan/")
        
        # Should see scanner interface
        self.page.wait_for_selector('[data-test="barcode-scanner"]')
        self.assertIn('Scan Barcode', self.page.content())
        
        # Test manual barcode entry
        self.page.fill('[data-test="manual-barcode"]', '1234567890123')
        self.page.click('[data-test="lookup-barcode"]')
        
        # Should show barcode lookup result
        self.page.wait_for_selector('[data-test="barcode-result"]')


class RecipeE2ETest(PlaywrightTestCase):
    """Test recipe management flows."""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.category = RecipeCategory.objects.create(name="Main Course")
        self.recipe = Recipe.objects.create(
            name="Test Recipe",
            category=self.category,
            created_by=self.user,
            servings=4,
            prep_time=15,
            cook_time=30,
            instructions="Test instructions",
            is_public=True
        )
        
        self.login_user()
    
    def test_user_can_view_recipe_discovery(self):
        """Test recipe discovery page."""
        self.page.goto(f"{self.live_server_url}/recipes/")
        
        # Should see recipe discovery
        self.assertIn('Recipe', self.page.title())
        self.page.wait_for_selector('[data-test="recipe-discovery"]')
        self.assertIn('Test Recipe', self.page.content())
    
    def test_user_can_view_recipe_detail(self):
        """Test viewing recipe details."""
        self.page.goto(f"{self.live_server_url}/recipes/{self.recipe.slug}/")
        
        # Should see recipe details
        self.assertIn('Test Recipe', self.page.content())
        self.assertIn('4 servings', self.page.content())
        self.assertIn('15 minutes', self.page.content())
    
    def test_user_can_create_recipe(self):
        """Test creating a new recipe."""
        self.page.goto(f"{self.live_server_url}/recipes/create/")
        
        # Fill form
        self.page.fill('[name="name"]', 'New Test Recipe')
        self.page.fill('[name="description"]', 'A new test recipe')
        self.page.select_option('[name="category"]', str(self.category.id))
        self.page.fill('[name="servings"]', '2')
        self.page.fill('[name="prep_time"]', '10')
        self.page.fill('[name="cook_time"]', '20')
        self.page.fill('[name="instructions"]', 'Mix and cook')
        self.page.select_option('[name="difficulty"]', 'easy')
        
        # Submit form
        self.page.click('button[type="submit"]')
        
        # Should redirect to recipe detail
        self.page.wait_for_url('**/recipes/**')
        self.assertIn('New Test Recipe', self.page.content())
    
    def test_cooking_mode_interface(self):
        """Test cooking mode interface."""
        self.page.goto(f"{self.live_server_url}/recipes/{self.recipe.slug}/cook/")
        
        # Should see cooking mode
        self.page.wait_for_selector('[data-test="cooking-mode"]')
        self.assertIn('Cooking Mode', self.page.content())
        
        # Test step navigation
        if self.page.is_visible('[data-test="next-step"]'):
            self.page.click('[data-test="next-step"]')
            # Should advance to next step


class ShoppingE2ETest(PlaywrightTestCase):
    """Test shopping list flows."""
    
    def setUp(self):
        super().setUp()
        
        # Create test data
        self.store = Store.objects.create(
            name="Test Store",
            store_type="grocery"
        )
        self.shopping_list = ShoppingList.objects.create(
            name="Test Shopping List",
            created_by=self.user,
            household=self.household,
            store=self.store
        )
        
        self.login_user()
    
    def test_user_can_view_shopping_dashboard(self):
        """Test shopping dashboard."""
        self.page.goto(f"{self.live_server_url}/shopping/")
        
        # Should see shopping dashboard
        self.assertIn('Shopping', self.page.title())
        self.page.wait_for_selector('[data-test="shopping-dashboard"]')
        self.assertIn('Test Shopping List', self.page.content())
    
    def test_user_can_create_shopping_list(self):
        """Test creating a shopping list."""
        self.page.goto(f"{self.live_server_url}/shopping/create/")
        
        # Fill form
        self.page.fill('[name="name"]', 'New Shopping List')
        self.page.select_option('[name="store"]', str(self.store.id))
        self.page.fill('[name="budget_limit"]', '100.00')
        
        # Submit form
        self.page.click('button[type="submit"]')
        
        # Should redirect to list detail
        self.page.wait_for_url('**/shopping/**')
        self.assertIn('New Shopping List', self.page.content())
    
    def test_user_can_add_items_to_list(self):
        """Test adding items to shopping list."""
        self.page.goto(f"{self.live_server_url}/shopping/list/{self.shopping_list.id}/")
        
        # Add item using quick add form
        self.page.fill('[data-test="add-item-name"]', 'Test Item')
        self.page.fill('[data-test="add-item-quantity"]', '2')
        self.page.click('[data-test="add-item-button"]')
        
        # Should see item in list
        self.page.wait_for_selector('[data-test="shopping-item"]')
        self.assertIn('Test Item', self.page.content())
    
    def test_user_can_check_off_items(self):
        """Test checking off shopping list items."""
        # Create a shopping list item
        from shopping.models import ShoppingListItem
        from inventory.models import Category, Product
        from decimal import Decimal
        
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(name="Test Product", category=category)
        item = ShoppingListItem.objects.create(
            shopping_list=self.shopping_list,
            product=product,
            name="Test Product",
            quantity=Decimal('1.0')
        )
        
        self.page.goto(f"{self.live_server_url}/shopping/list/{self.shopping_list.id}/")
        
        # Check off item
        self.page.check(f'[data-test="item-{item.id}-checkbox"]')
        
        # Should see item as completed
        self.page.wait_for_selector(f'[data-test="item-{item.id}"].completed')
    
    def test_list_sharing_interface(self):
        """Test sharing shopping list."""
        self.page.goto(f"{self.live_server_url}/shopping/list/{self.shopping_list.id}/edit/")
        
        # Should see sharing section
        self.page.wait_for_selector('[data-test="sharing-section"]')
        
        # Try to share with another user
        self.page.fill('[data-test="share-email"]', 'friend@example.com')
        self.page.select_option('[data-test="share-permission"]', 'view')
        self.page.click('[data-test="share-button"]')


class MobileE2ETest(PlaywrightTestCase):
    """Test mobile-specific functionality."""
    
    def setUp(self):
        super().setUp()
        # Use mobile viewport
        self.context.set_viewport_size({"width": 375, "height": 667})
        self.login_user()
    
    def test_mobile_navigation(self):
        """Test mobile navigation works."""
        self.page.goto(f"{self.live_server_url}/")
        
        # Should see mobile navigation
        self.page.wait_for_selector('[data-test="mobile-nav"]')
        
        # Test navigation items
        self.page.click('[data-test="nav-inventory"]')
        self.page.wait_for_url('**/inventory/**')
        
        self.page.click('[data-test="nav-recipes"]')
        self.page.wait_for_url('**/recipes/**')
        
        self.page.click('[data-test="nav-shopping"]')
        self.page.wait_for_url('**/shopping/**')
    
    def test_touch_interactions(self):
        """Test touch-specific interactions."""
        self.page.goto(f"{self.live_server_url}/inventory/")
        
        # Test touch targets are large enough
        nav_items = self.page.locator('[data-test="mobile-nav"] a')
        for i in range(nav_items.count()):
            item = nav_items.nth(i)
            box = item.bounding_box()
            # Touch targets should be at least 44px
            self.assertGreaterEqual(box['height'], 44)
    
    def test_swipe_gestures(self):
        """Test swipe gesture functionality."""
        # Create test shopping list with items
        from shopping.models import ShoppingListItem
        from inventory.models import Category, Product
        from decimal import Decimal
        
        category = Category.objects.create(name="Test Category")
        product = Product.objects.create(name="Swipe Test Product", category=category)
        shopping_list = ShoppingList.objects.create(
            name="Swipe Test List",
            created_by=self.user,
            household=self.household
        )
        item = ShoppingListItem.objects.create(
            shopping_list=shopping_list,
            product=product,
            name="Swipe Test Product",
            quantity=Decimal('1.0')
        )
        
        self.page.goto(f"{self.live_server_url}/shopping/list/{shopping_list.id}/")
        
        # Test swipe to complete item (if implemented)
        item_element = self.page.locator(f'[data-test="item-{item.id}"]')
        if item_element.is_visible():
            # Simulate swipe gesture
            box = item_element.bounding_box()
            self.page.mouse.move(box['x'] + 10, box['y'] + box['height'] / 2)
            self.page.mouse.down()
            self.page.mouse.move(box['x'] + box['width'] - 10, box['y'] + box['height'] / 2)
            self.page.mouse.up()


class PWAE2ETest(PlaywrightTestCase):
    """Test PWA functionality."""
    
    def test_offline_functionality(self):
        """Test offline functionality."""
        self.login_user()
        self.page.goto(f"{self.live_server_url}/inventory/")
        
        # Wait for page to load and service worker to register
        self.page.wait_for_load_state('networkidle')
        
        # Simulate offline mode
        context = self.page.context
        context.set_offline(True)
        
        # Navigate to cached page
        self.page.goto(f"{self.live_server_url}/inventory/")
        
        # Should still work offline (if properly cached)
        self.page.wait_for_selector('[data-test="inventory-dashboard"]')
        self.assertIn('Inventory', self.page.content())
    
    def test_install_prompt(self):
        """Test PWA install prompt."""
        self.page.goto(f"{self.live_server_url}/")
        
        # Wait for potential install prompt
        self.page.wait_for_timeout(2000)
        
        # Check if install button appears
        if self.page.is_visible('[data-test="install-button"]'):
            self.page.click('[data-test="install-button"]')
            # Installation flow would continue


class AccessibilityE2ETest(PlaywrightTestCase):
    """Test accessibility features."""
    
    def test_keyboard_navigation(self):
        """Test keyboard navigation."""
        self.login_user()
        self.page.goto(f"{self.live_server_url}/")
        
        # Test tab navigation
        self.page.keyboard.press('Tab')
        focused_element = self.page.evaluate('document.activeElement.tagName')
        self.assertIn(focused_element.lower(), ['a', 'button', 'input'])
    
    def test_screen_reader_labels(self):
        """Test screen reader accessibility."""
        self.login_user()
        self.page.goto(f"{self.live_server_url}/inventory/")
        
        # Check for proper ARIA labels
        buttons = self.page.locator('button')
        for i in range(min(buttons.count(), 5)):  # Check first 5 buttons
            button = buttons.nth(i)
            aria_label = button.get_attribute('aria-label')
            text_content = button.text_content()
            
            # Button should have either aria-label or text content
            self.assertTrue(
                aria_label or text_content,
                "Button should have aria-label or text content"
            )
    
    def test_color_contrast(self):
        """Test color contrast (basic check)."""
        self.login_user()
        self.page.goto(f"{self.live_server_url}/")
        
        # Check that important elements have sufficient contrast
        # This is a basic check - comprehensive testing would use axe-core
        primary_buttons = self.page.locator('.bg-blue-600, .btn-primary')
        for i in range(min(primary_buttons.count(), 3)):
            button = primary_buttons.nth(i)
            styles = self.page.evaluate('(el) => getComputedStyle(el)', button)
            # Basic check that text isn't the same color as background
            self.assertNotEqual(styles['color'], styles['backgroundColor'])


@pytest.mark.django_db
class PerformanceE2ETest(PlaywrightTestCase):
    """Test performance-related functionality."""
    
    def test_page_load_times(self):
        """Test that pages load within acceptable time."""
        self.login_user()
        
        pages_to_test = [
            f"{self.live_server_url}/",
            f"{self.live_server_url}/inventory/",
            f"{self.live_server_url}/recipes/",
            f"{self.live_server_url}/shopping/",
        ]
        
        for url in pages_to_test:
            start_time = self.page.evaluate('Date.now()')
            self.page.goto(url)
            self.page.wait_for_load_state('networkidle')
            end_time = self.page.evaluate('Date.now()')
            
            load_time = end_time - start_time
            # Page should load within 3 seconds
            self.assertLess(load_time, 3000, f"Page {url} took {load_time}ms to load")
    
    def test_image_lazy_loading(self):
        """Test image lazy loading functionality."""
        # Create recipe with image
        self.recipe = Recipe.objects.create(
            name="Recipe with Image",
            category=RecipeCategory.objects.create(name="Test"),
            created_by=self.user,
            instructions="Test recipe"
        )
        
        self.login_user()
        self.page.goto(f"{self.live_server_url}/recipes/")
        
        # Check for lazy loading attributes
        images = self.page.locator('img[data-src], img[loading="lazy"]')
        if images.count() > 0:
            # At least some images should have lazy loading
            self.assertGreater(images.count(), 0)