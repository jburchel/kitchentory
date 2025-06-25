# Contributing to Kitchentory

Thank you for your interest in contributing to Kitchentory! This document provides guidelines and information for contributors.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [Contributing Process](#contributing-process)
5. [Coding Standards](#coding-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Issue Reporting](#issue-reporting)
10. [Community](#community)

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone, regardless of age, body size, disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes:**
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team at conduct@kitchentory.com. All complaints will be reviewed and investigated promptly and fairly.

## Getting Started

### Prerequisites

- Python 3.9+
- Node.js 16+ (for frontend development)
- PostgreSQL 13+
- Redis 6+
- Git

### Areas for Contribution

We welcome contributions in various areas:

- **Backend Development**: Django, API endpoints, database optimization
- **Frontend Development**: JavaScript, CSS, mobile responsiveness
- **Mobile Development**: PWA features, offline functionality
- **Testing**: Unit tests, integration tests, E2E tests
- **Documentation**: User guides, API docs, tutorials
- **Design**: UI/UX improvements, accessibility
- **DevOps**: CI/CD, deployment scripts, monitoring
- **Translation**: Internationalization and localization

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/yourusername/kitchentory.git
cd kitchentory

# Add upstream remote
git remote add upstream https://github.com/kitchentory/kitchentory.git
```

### 2. Set Up Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
npm install

# Copy environment file
cp .env.example .env
# Edit .env with your local settings
```

### 3. Database Setup

```bash
# Create database
createdb kitchentory_dev

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data (optional)
python manage.py loaddata fixtures/sample_data.json
```

### 4. Run Development Server

```bash
# Start Django development server
python manage.py runserver

# In another terminal, start frontend build process
npm run dev

# Start Redis (if using caching/celery)
redis-server

# Start Celery worker (if needed)
celery -A kitchentory worker -l info
```

## Contributing Process

### 1. Choose an Issue

- Look for issues labeled `good first issue` for newcomers
- Check issues labeled `help wanted` for areas needing contribution
- Comment on the issue to let others know you're working on it
- For new features, create an issue first to discuss the approach

### 2. Create a Branch

```bash
# Update your fork
git checkout main
git pull upstream main

# Create a feature branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

### 3. Make Changes

- Follow the coding standards outlined below
- Write tests for new functionality
- Update documentation as needed
- Keep commits atomic and well-described

### 4. Test Your Changes

```bash
# Run the full test suite
python manage.py test

# Run specific tests
python manage.py test inventory.tests.test_models

# Check code style
flake8 .
black --check .

# Run frontend tests
npm test

# Run E2E tests (optional)
python manage.py test tests.test_e2e
```

### 5. Submit Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create pull request on GitHub
```

## Coding Standards

### Python/Django Standards

#### Code Style

We use [Black](https://black.readthedocs.io/) for code formatting and [flake8](https://flake8.pycqa.org/) for linting.

```bash
# Format code
black .

# Check linting
flake8 .
```

#### Django Best Practices

**Models:**
```python
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class InventoryItem(models.Model):
    """Model representing an inventory item."""
    
    # Use descriptive field names
    current_quantity = models.DecimalField(
        _('current quantity'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Current quantity in stock')
    )
    
    class Meta:
        verbose_name = _('inventory item')
        verbose_name_plural = _('inventory items')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.current_quantity} {self.unit}"
    
    def get_absolute_url(self):
        return reverse('inventory:item_detail', kwargs={'pk': self.pk})
```

**Views:**
```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.db.models import Q


class InventoryListView(LoginRequiredMixin, ListView):
    """List view for inventory items."""
    
    model = InventoryItem
    template_name = 'inventory/item_list.html'
    context_object_name = 'items'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter items by current user's household."""
        queryset = super().get_queryset()
        return queryset.filter(
            household__members=self.request.user
        ).select_related('product', 'location')
    
    def get_context_data(self, **kwargs):
        """Add additional context."""
        context = super().get_context_data(**kwargs)
        context['total_items'] = self.get_queryset().count()
        return context
```

#### API Standards

```python
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated


class InventoryItemSerializer(serializers.ModelSerializer):
    """Serializer for inventory items."""
    
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = InventoryItem
        fields = [
            'id', 'product', 'product_name', 'current_quantity',
            'unit', 'expiration_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_current_quantity(self, value):
        """Validate quantity is positive."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be positive")
        return value


class InventoryItemViewSet(viewsets.ModelViewSet):
    """ViewSet for inventory items."""
    
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['product', 'location']
    search_fields = ['product__name', 'notes']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter by user's household."""
        return InventoryItem.objects.filter(
            household__members=self.request.user
        ).select_related('product', 'location')
```

### Frontend Standards

#### JavaScript Style

```javascript
// Use modern ES6+ syntax
class InventoryManager {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
        this.items = new Map();
    }
    
    async loadItems() {
        try {
            const response = await fetch(`${this.apiUrl}/inventory/`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            this.items = new Map(data.results.map(item => [item.id, item]));
            return this.items;
        } catch (error) {
            console.error('Failed to load inventory items:', error);
            throw error;
        }
    }
    
    updateQuantity(itemId, newQuantity) {
        if (!this.items.has(itemId)) {
            throw new Error(`Item ${itemId} not found`);
        }
        
        if (newQuantity < 0) {
            throw new Error('Quantity cannot be negative');
        }
        
        const item = this.items.get(itemId);
        item.current_quantity = newQuantity;
        this.items.set(itemId, item);
    }
}
```

#### CSS Guidelines

```css
/* Use BEM methodology for class names */
.inventory-item {
    display: flex;
    align-items: center;
    padding: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
}

.inventory-item__image {
    width: 4rem;
    height: 4rem;
    object-fit: cover;
    border-radius: 0.25rem;
}

.inventory-item__content {
    flex: 1;
    margin-left: 1rem;
}

.inventory-item__title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text-primary);
}

.inventory-item__meta {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
}

/* Use CSS custom properties for theming */
:root {
    --color-primary: #3b82f6;
    --color-secondary: #64748b;
    --color-success: #10b981;
    --color-warning: #f59e0b;
    --color-error: #ef4444;
    
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --border-color: #e5e7eb;
    --background-color: #ffffff;
}

/* Mobile-first responsive design */
.container {
    padding: 1rem;
}

@media (min-width: 768px) {
    .container {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
}
```

### Database Standards

#### Migration Guidelines

```python
# migrations/0001_initial.py
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Initial migration for inventory app.
    
    Creates basic models for products, categories, and inventory items.
    """
    
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(primary_key=True)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name_plural': 'categories',
                'ordering': ['name'],
            },
        ),
        # Always include descriptive comments for complex operations
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY idx_inventory_expiration ON inventory_inventoryitem(expiration_date) WHERE expiration_date IS NOT NULL;",
            reverse_sql="DROP INDEX IF EXISTS idx_inventory_expiration;",
        ),
    ]
```

## Testing Guidelines

### Test Structure

```python
# tests/test_models.py
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from inventory.models import Category, Product, InventoryItem


User = get_user_model()


class InventoryItemModelTest(TestCase):
    """Test cases for InventoryItem model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category
        )
    
    def test_create_inventory_item(self):
        """Test creating an inventory item."""
        item = InventoryItem.objects.create(
            product=self.product,
            current_quantity=Decimal('5.0'),
            unit='pieces'
        )
        
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.current_quantity, Decimal('5.0'))
        self.assertEqual(item.unit, 'pieces')
        self.assertIsNotNone(item.created_at)
    
    def test_negative_quantity_validation(self):
        """Test that negative quantities are not allowed."""
        with self.assertRaises(ValidationError):
            item = InventoryItem(
                product=self.product,
                current_quantity=Decimal('-1.0'),
                unit='pieces'
            )
            item.full_clean()
    
    def test_string_representation(self):
        """Test string representation of inventory item."""
        item = InventoryItem.objects.create(
            product=self.product,
            current_quantity=Decimal('3.0'),
            unit='kg'
        )
        
        expected = f"{self.product.name} - 3.0 kg"
        self.assertEqual(str(item), expected)
```

### Test Coverage

Aim for high test coverage:

```bash
# Run tests with coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

**Minimum coverage requirements:**
- Models: 95%
- Views: 85%
- Utilities: 90%
- API endpoints: 90%

## Documentation

### Code Documentation

```python
def calculate_expiration_status(expiration_date):
    """
    Calculate the expiration status of an item.
    
    Args:
        expiration_date (date): The expiration date of the item.
        
    Returns:
        str: One of 'fresh', 'expiring_soon', or 'expired'.
        
    Examples:
        >>> from datetime import date, timedelta
        >>> tomorrow = date.today() + timedelta(days=1)
        >>> calculate_expiration_status(tomorrow)
        'expiring_soon'
    """
    if not expiration_date:
        return 'unknown'
    
    today = date.today()
    days_until_expiry = (expiration_date - today).days
    
    if days_until_expiry < 0:
        return 'expired'
    elif days_until_expiry <= 3:
        return 'expiring_soon'
    else:
        return 'fresh'
```

### API Documentation

Use detailed docstrings for API endpoints:

```python
class InventoryItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inventory items.
    
    Provides CRUD operations for inventory items within the user's household.
    
    list:
    Return a list of inventory items for the current user's household.
    Supports filtering by product, location, and expiration status.
    
    create:
    Create a new inventory item.
    
    retrieve:
    Return details of a specific inventory item.
    
    update:
    Update an existing inventory item.
    
    destroy:
    Delete an inventory item.
    """
```

## Pull Request Process

### 1. Pre-submission Checklist

- [ ] Code follows style guidelines
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Descriptive commit messages
- [ ] PR description explains changes

### 2. PR Description Template

```markdown
## Description
Brief description of changes made.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed

## Screenshots (if applicable)
Add screenshots for UI changes.

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added and passing
```

### 3. Review Process

1. **Automated checks**: CI/CD pipeline runs tests and linting
2. **Code review**: At least one maintainer reviews the PR
3. **Testing**: Reviewer tests changes locally if needed
4. **Approval**: PR approved and merged

### 4. Merge Requirements

- All CI checks must pass
- At least one approving review from a maintainer
- No unresolved conversations
- Branch is up to date with main

## Issue Reporting

### Bug Reports

When reporting bugs, include:

1. **Environment details**:
   - Operating system
   - Python version
   - Browser (for frontend issues)
   - Kitchentory version

2. **Steps to reproduce**:
   - Clear, numbered steps
   - Expected vs. actual behavior
   - Screenshots/videos if helpful

3. **Additional context**:
   - Error messages
   - Log output
   - Related issues

### Feature Requests

For feature requests, provide:

1. **Problem description**: What problem does this solve?
2. **Proposed solution**: How should it work?
3. **Alternatives considered**: Other approaches considered
4. **Use cases**: Who would benefit and how?

### Security Issues

For security vulnerabilities:

1. **Do not** create a public issue
2. Email security@kitchentory.com
3. Include detailed description
4. Provide proof of concept if possible

## Community

### Communication Channels

- **GitHub Discussions**: General questions and community discussions
- **Discord**: Real-time chat for developers
- **Email**: contact@kitchentory.com for general inquiries

### Getting Help

- Check existing issues and documentation first
- Use GitHub Discussions for questions
- Join our Discord for real-time help
- Attend monthly community calls (announced in Discord)

### Recognition

Contributors are recognized through:

- Contributors list in README
- Release notes mentions
- Annual contributor awards
- Speaking opportunities at community events

## Development Workflow

### Branch Naming

- Feature branches: `feature/description` or `feature/issue-number`
- Bug fixes: `fix/description` or `fix/issue-number`
- Documentation: `docs/description`
- Refactoring: `refactor/description`

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

**Examples:**
```
feat(inventory): add barcode scanning functionality

Add support for scanning product barcodes using device camera.
Includes validation for common barcode formats (EAN-13, UPC-A).

Closes #123

fix(api): handle empty search queries correctly

Previously empty search queries would return 500 error.
Now returns empty results with proper pagination.

docs(api): update authentication examples

Add examples for token refresh and logout endpoints.
```

### Release Process

1. **Version bumping**: Use semantic versioning (MAJOR.MINOR.PATCH)
2. **Changelog**: Update CHANGELOG.md with new features and fixes
3. **Testing**: Full test suite must pass
4. **Tagging**: Create git tag with version number
5. **Deployment**: Automated deployment to staging, then production

Thank you for contributing to Kitchentory! Your contributions help make kitchen management easier for everyone.