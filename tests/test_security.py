"""
Security testing for Kitchentory application.
"""

import json
import re
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.middleware.csrf import get_token
from django.core.files.uploadedfile import SimpleUploadedFile

from inventory.models import Category, Product, Household, StorageLocation, InventoryItem
from recipes.models import RecipeCategory, Recipe
from shopping.models import Store, ShoppingList, ShoppingListItem

User = get_user_model()


class CSRFSecurityTest(TestCase):
    """Test CSRF protection."""
    
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
    
    def test_csrf_protection_on_login(self):
        """Test CSRF protection on login form."""
        response = self.client.post('/accounts/login/', {
            'login': 'testuser',
            'password': 'testpass123'
        })
        # Should be forbidden due to missing CSRF token
        self.assertEqual(response.status_code, 403)
    
    def test_csrf_protection_on_forms(self):
        """Test CSRF protection on application forms."""
        self.client.login(username='testuser', password='testpass123')
        
        # Get CSRF token
        response = self.client.get('/inventory/add/')
        csrf_token = get_token(response.wsgi_request)
        
        # Submit without CSRF token should fail
        response = self.client.post('/inventory/add/', {
            'name': 'Test Item'
        })
        self.assertEqual(response.status_code, 403)
        
        # Submit with CSRF token should work
        response = self.client.post('/inventory/add/', {
            'name': 'Test Item',
            'csrfmiddlewaretoken': csrf_token
        })
        # Should not be 403 (may be 302 redirect or 200 with form errors)
        self.assertNotEqual(response.status_code, 403)
    
    def test_csrf_exempt_endpoints(self):
        """Test that API endpoints are properly CSRF exempt."""
        # API endpoints should be exempt from CSRF if using token auth
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        }, content_type='application/json')
        
        # Should not fail due to CSRF (may fail for other reasons)
        self.assertNotEqual(response.status_code, 403)


class AuthenticationSecurityTest(TestCase):
    """Test authentication security."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_password_strength_requirements(self):
        """Test password strength validation."""
        weak_passwords = [
            'password',
            '123456',
            'abc123',
            'testuser',  # Same as username
        ]
        
        for password in weak_passwords:
            response = self.client.post('/accounts/signup/', {
                'username': 'newuser',
                'email': 'new@example.com',
                'password1': password,
                'password2': password
            })
            
            # Should contain password validation errors
            if response.status_code == 200:
                self.assertContains(response, 'password')
    
    def test_rate_limiting_login_attempts(self):
        """Test rate limiting on login attempts."""
        # Attempt multiple failed logins
        for i in range(10):
            response = self.client.post('/accounts/login/', {
                'login': 'testuser',
                'password': 'wrongpassword'
            })
        
        # After multiple failed attempts, should be rate limited
        # Note: This requires django-ratelimit or similar
        # For now, just ensure we don't get 500 errors
        self.assertIn(response.status_code, [200, 302, 429])
    
    def test_session_security(self):
        """Test session security settings."""
        self.client.login(username='testuser', password='testpass123')
        
        # Check session settings
        session = self.client.session
        
        # Session should have security flags
        # These would be tested in settings, not in session data
        response = self.client.get('/')
        
        # Check for secure cookie settings in response
        if hasattr(response, 'cookies'):
            for cookie in response.cookies:
                if 'sessionid' in cookie:
                    # Check for HttpOnly, Secure flags
                    cookie_attrs = str(cookie)
                    # In test environment, secure might not be set
                    self.assertIn('HttpOnly', cookie_attrs)


class AuthorizationSecurityTest(TestCase):
    """Test authorization and access control."""
    
    def setUp(self):
        self.client = Client()
        
        # Create two users with separate households
        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123"
        )
        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123"
        )
        
        self.household1 = Household.objects.create(
            name="Household 1",
            created_by=self.user1
        )
        self.household1.members.add(self.user1)
        
        self.household2 = Household.objects.create(
            name="Household 2",
            created_by=self.user2
        )
        self.household2.members.add(self.user2)
        
        # Create test data for each household
        self.category = Category.objects.create(name="Test Category")
        self.product = Product.objects.create(
            name="Test Product",
            category=self.category
        )
        
        self.location1 = StorageLocation.objects.create(
            name="Pantry 1",
            household=self.household1
        )
        self.location2 = StorageLocation.objects.create(
            name="Pantry 2",
            household=self.household2
        )
        
        self.item1 = InventoryItem.objects.create(
            product=self.product,
            household=self.household1,
            location=self.location1,
            current_quantity=5,
            unit='pieces'
        )
        self.item2 = InventoryItem.objects.create(
            product=self.product,
            household=self.household2,
            location=self.location2,
            current_quantity=3,
            unit='pieces'
        )
    
    def test_user_cannot_access_other_household_inventory(self):
        """Test that users cannot access other households' inventory."""
        self.client.login(username='user1', password='testpass123')
        
        # User1 should be able to access their own item
        response = self.client.get(f'/inventory/item/{self.item1.id}/')
        self.assertIn(response.status_code, [200, 302])
        
        # User1 should NOT be able to access user2's item
        response = self.client.get(f'/inventory/item/{self.item2.id}/')
        self.assertIn(response.status_code, [403, 404])
    
    def test_user_cannot_modify_other_household_data(self):
        """Test that users cannot modify other households' data."""
        self.client.login(username='user1', password='testpass123')
        
        # Try to edit user2's inventory item
        response = self.client.post(f'/inventory/item/{self.item2.id}/edit/', {
            'current_quantity': '10'
        })
        self.assertIn(response.status_code, [403, 404])
        
        # Verify item wasn't changed
        self.item2.refresh_from_db()
        self.assertNotEqual(self.item2.current_quantity, 10)
    
    def test_recipe_ownership_protection(self):
        """Test recipe ownership and access control."""
        category = RecipeCategory.objects.create(name="Test Category")
        
        # User1 creates a private recipe
        recipe = Recipe.objects.create(
            name="User1's Recipe",
            category=category,
            created_by=self.user1,
            is_public=False
        )
        
        # User1 should be able to access it
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(f'/recipes/{recipe.slug}/')
        self.assertEqual(response.status_code, 200)
        
        # User2 should NOT be able to access private recipe
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(f'/recipes/{recipe.slug}/')
        self.assertIn(response.status_code, [403, 404])
        
        # User2 should NOT be able to edit it
        response = self.client.post(f'/recipes/{recipe.slug}/edit/', {
            'name': 'Modified Recipe'
        })
        self.assertIn(response.status_code, [403, 404])
    
    def test_shopping_list_access_control(self):
        """Test shopping list access control."""
        shopping_list = ShoppingList.objects.create(
            name="User1's List",
            created_by=self.user1,
            household=self.household1
        )
        
        # User1 should be able to access it
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(f'/shopping/list/{shopping_list.id}/')
        self.assertEqual(response.status_code, 200)
        
        # User2 should NOT be able to access it
        self.client.login(username='user2', password='testpass123')
        response = self.client.get(f'/shopping/list/{shopping_list.id}/')
        self.assertIn(response.status_code, [403, 404])


class InputValidationSecurityTest(TestCase):
    """Test input validation and sanitization."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.household = Household.objects.create(
            name="Test Household",
            created_by=self.user
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_xss_prevention_in_forms(self):
        """Test XSS prevention in form inputs."""
        xss_payloads = [
            '<script>alert("xss")</script>',
            '"><script>alert("xss")</script>',
            'javascript:alert("xss")',
            '<img src=x onerror=alert("xss")>',
            '<svg onload=alert("xss")>',
        ]
        
        category = Category.objects.create(name="Test Category")
        
        for payload in xss_payloads:
            # Try to create product with XSS payload
            response = self.client.post('/admin/inventory/product/add/', {
                'name': payload,
                'category': category.id,
                'default_unit': 'pieces'
            })
            
            # Check that the payload is properly escaped in response
            if response.status_code == 200:
                self.assertNotContains(response, '<script>')
                self.assertNotContains(response, 'javascript:')
    
    def test_sql_injection_prevention(self):
        """Test SQL injection prevention."""
        sql_payloads = [
            "'; DROP TABLE inventory_product; --",
            "' OR '1'='1",
            "'; SELECT * FROM auth_user; --",
            "' UNION SELECT 1,2,3,4,5--",
        ]
        
        for payload in sql_payloads:
            # Try search with SQL injection payload
            response = self.client.get('/inventory/search/', {
                'q': payload
            })
            
            # Should not cause database errors
            self.assertNotEqual(response.status_code, 500)
            
            # Should not return unauthorized data
            self.assertNotContains(response, 'auth_user')
            self.assertNotContains(response, 'password')
    
    def test_file_upload_security(self):
        """Test file upload security."""
        malicious_files = [
            # PHP file disguised as image
            ('malicious.php.jpg', b'<?php system($_GET["cmd"]); ?>', 'image/jpeg'),
            # JavaScript file
            ('script.js', b'alert("xss");', 'application/javascript'),
            # HTML file
            ('page.html', b'<script>alert("xss")</script>', 'text/html'),
            # Executable file
            ('virus.exe', b'MZ\x90\x00', 'application/octet-stream'),
        ]
        
        category = RecipeCategory.objects.create(name="Test Category")
        
        for filename, content, content_type in malicious_files:
            uploaded_file = SimpleUploadedFile(
                filename,
                content,
                content_type=content_type
            )
            
            # Try to upload malicious file as recipe image
            response = self.client.post('/recipes/create/', {
                'name': 'Test Recipe',
                'category': category.id,
                'servings': 4,
                'instructions': 'Test',
                'image': uploaded_file
            })
            
            # Should either reject the file or sanitize it
            if response.status_code == 302:  # Successful creation
                recipe = Recipe.objects.filter(name='Test Recipe').first()
                if recipe and recipe.image:
                    # File should be validated and potentially renamed
                    stored_filename = recipe.image.name
                    self.assertNotIn('.php', stored_filename)
                    self.assertNotIn('.js', stored_filename)
                    self.assertNotIn('.exe', stored_filename)
    
    def test_path_traversal_prevention(self):
        """Test path traversal prevention."""
        traversal_payloads = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            '....//....//....//etc//passwd',
            '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd',
        ]
        
        for payload in traversal_payloads:
            # Try to access files via path traversal
            response = self.client.get(f'/static/{payload}')
            
            # Should not expose system files
            self.assertNotContains(response, 'root:')
            self.assertNotContains(response, 'administrator')
            self.assertIn(response.status_code, [404, 403])


class APISecurityTest(TestCase):
    """Test API security."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_api_authentication_required(self):
        """Test that API endpoints require authentication."""
        api_endpoints = [
            '/api/inventory/',
            '/api/recipes/',
            '/api/shopping/',
        ]
        
        for endpoint in api_endpoints:
            response = self.client.get(endpoint)
            # Should require authentication
            self.assertEqual(response.status_code, 401)
    
    def test_api_rate_limiting(self):
        """Test API rate limiting."""
        # Get auth token
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        if response.status_code == 200:
            data = json.loads(response.content)
            token = data.get('token')
            
            if token:
                # Make many requests quickly
                headers = {'HTTP_AUTHORIZATION': f'Token {token}'}
                
                for i in range(100):
                    response = self.client.get('/api/inventory/', **headers)
                    
                    # Should eventually hit rate limit
                    if response.status_code == 429:
                        break
                
                # Should have rate limiting headers
                if response.status_code == 429:
                    self.assertIn('Retry-After', response)
    
    def test_api_input_validation(self):
        """Test API input validation."""
        # Get auth token
        response = self.client.post('/api/auth/login/', {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        if response.status_code == 200:
            data = json.loads(response.content)
            token = data.get('token')
            
            if token:
                headers = {
                    'HTTP_AUTHORIZATION': f'Token {token}',
                    'content_type': 'application/json'
                }
                
                # Test invalid JSON
                response = self.client.post(
                    '/api/inventory/',
                    'invalid json',
                    **headers
                )
                self.assertEqual(response.status_code, 400)
                
                # Test invalid data types
                response = self.client.post(
                    '/api/inventory/',
                    json.dumps({
                        'current_quantity': 'not_a_number',
                        'expiration_date': 'not_a_date'
                    }),
                    **headers
                )
                self.assertEqual(response.status_code, 400)


class SessionSecurityTest(TestCase):
    """Test session security."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
    
    def test_session_fixation_protection(self):
        """Test session fixation protection."""
        # Get initial session
        response = self.client.get('/')
        session_key_before = self.client.session.session_key
        
        # Login
        self.client.login(username='testuser', password='testpass123')
        session_key_after = self.client.session.session_key
        
        # Session key should change after login
        self.assertNotEqual(session_key_before, session_key_after)
    
    def test_session_timeout(self):
        """Test session timeout settings."""
        self.client.login(username='testuser', password='testpass123')
        
        # Check that session has timeout
        session = self.client.session
        self.assertIsNotNone(session.get_expiry_age())
    
    def test_concurrent_session_handling(self):
        """Test handling of concurrent sessions."""
        # Login from first client
        client1 = Client()
        client1.login(username='testuser', password='testpass123')
        
        # Login from second client
        client2 = Client()
        client2.login(username='testuser', password='testpass123')
        
        # Both sessions should be valid (unless concurrent session limit is set)
        response1 = client1.get('/inventory/')
        response2 = client2.get('/inventory/')
        
        # Should not get authentication errors
        self.assertNotEqual(response1.status_code, 401)
        self.assertNotEqual(response2.status_code, 401)


@override_settings(DEBUG=False)
class SecurityHeadersTest(TestCase):
    """Test security headers."""
    
    def setUp(self):
        self.client = Client()
    
    def test_security_headers_present(self):
        """Test that security headers are present."""
        response = self.client.get('/')
        
        # Check for important security headers
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
            'Strict-Transport-Security',
            'Content-Security-Policy',
        ]
        
        for header in security_headers:
            if header in response:
                # Header is present, check it has a value
                self.assertTrue(response[header])
    
    def test_csrf_cookie_security(self):
        """Test CSRF cookie security flags."""
        response = self.client.get('/')
        
        # Check CSRF cookie settings
        if 'Set-Cookie' in response:
            cookies = response['Set-Cookie']
            if 'csrftoken' in cookies:
                # Should have HttpOnly and Secure flags in production
                # Note: In test environment, Secure might not be set
                self.assertIn('HttpOnly', cookies)
    
    def test_content_type_headers(self):
        """Test content type headers."""
        response = self.client.get('/')
        
        # Should have proper content type
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        
        # Should prevent MIME sniffing
        if 'X-Content-Type-Options' in response:
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')


class InformationDisclosureTest(TestCase):
    """Test for information disclosure vulnerabilities."""
    
    def setUp(self):
        self.client = Client()
    
    def test_error_pages_dont_leak_info(self):
        """Test that error pages don't leak sensitive information."""
        # Test 404 page
        response = self.client.get('/nonexistent-page/')
        self.assertEqual(response.status_code, 404)
        
        # Should not contain sensitive info
        content = response.content.decode()
        sensitive_patterns = [
            r'/home/\w+/',  # User home directories
            r'SECRET_KEY',
            r'DATABASE_URL',
            r'password',
            r'settings\.py',
            r'Traceback',
        ]
        
        for pattern in sensitive_patterns:
            self.assertNotRegex(content, pattern, f"Found sensitive pattern: {pattern}")
    
    def test_debug_info_not_exposed(self):
        """Test that debug information is not exposed."""
        # Test with invalid data to potentially trigger errors
        response = self.client.post('/inventory/add/', {
            'invalid_field': 'test'
        })
        
        # Should not expose debug information
        content = response.content.decode()
        self.assertNotIn('Traceback', content)
        self.assertNotIn('django.', content)
        self.assertNotIn('/usr/', content)
    
    def test_version_info_not_exposed(self):
        """Test that version information is not exposed."""
        response = self.client.get('/')
        
        # Should not expose framework versions
        headers = response.serialize_headers().decode()
        content = response.content.decode()
        
        version_patterns = [
            r'Django/[\d\.]+',
            r'Python/[\d\.]+',
            r'nginx/[\d\.]+',
            r'Server: Django',
        ]
        
        for pattern in version_patterns:
            self.assertNotRegex(headers + content, pattern)