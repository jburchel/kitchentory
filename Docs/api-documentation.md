# Kitchentory API Documentation

This document provides comprehensive documentation for the Kitchentory REST API.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Common Patterns](#common-patterns)
4. [Inventory API](#inventory-api)
5. [Recipe API](#recipe-api)
6. [Shopping API](#shopping-api)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [Examples](#examples)

## Overview

The Kitchentory API is a RESTful API that allows you to manage kitchen inventory, recipes, and shopping lists. All API endpoints return JSON responses and follow standard HTTP status codes.

**Base URL:** `https://api.kitchentory.com/api/`

**API Version:** v1

### Supported Formats
- Request: JSON
- Response: JSON

### Content Type
All requests should include the header:
```
Content-Type: application/json
```

## Authentication

The API uses token-based authentication. You must include a valid token in the Authorization header for all protected endpoints.

### Obtain Authentication Token

**Endpoint:** `POST /api/auth/login/`

**Request Body:**
```json
{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "token": "your_auth_token_here",
    "user": {
        "id": 1,
        "username": "your_username",
        "email": "your_email@example.com"
    }
}
```

### Using the Token

Include the token in the Authorization header of all subsequent requests:
```
Authorization: Token your_auth_token_here
```

### Logout

**Endpoint:** `POST /api/auth/logout/`

Invalidates the current token.

## Common Patterns

### Pagination

List endpoints support pagination with the following parameters:

- `page`: Page number (default: 1)
- `page_size`: Number of items per page (default: 20, max: 100)

**Response Format:**
```json
{
    "count": 150,
    "next": "https://api.kitchentory.com/api/inventory/?page=2",
    "previous": null,
    "results": [...]
}
```

### Filtering and Search

Many endpoints support filtering and search:

- `search`: General text search
- `category`: Filter by category ID
- `expired`: Filter expired items (true/false)
- `location`: Filter by storage location

**Example:**
```
GET /api/inventory/?search=tomato&expired=false&page_size=10
```

### Date Formats

All dates should be in ISO 8601 format: `YYYY-MM-DD`
All datetimes should be in ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`

## Inventory API

### List Inventory Items

**Endpoint:** `GET /api/inventory/`

**Parameters:**
- `search`: Search by product name
- `category`: Filter by category ID
- `location`: Filter by storage location ID
- `expired`: Filter expired items (true/false)
- `expiring_soon`: Items expiring within N days

**Response:**
```json
{
    "count": 25,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "product": {
                "id": 1,
                "name": "Organic Tomatoes",
                "category": {
                    "id": 1,
                    "name": "Vegetables"
                },
                "default_unit": "pieces"
            },
            "location": {
                "id": 1,
                "name": "Refrigerator",
                "household": 1
            },
            "current_quantity": "5.00",
            "unit": "pieces",
            "purchase_date": "2024-01-15",
            "expiration_date": "2024-01-22",
            "purchase_price": "4.99",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
    ]
}
```

### Get Inventory Item

**Endpoint:** `GET /api/inventory/{id}/`

**Response:**
```json
{
    "id": 1,
    "product": {
        "id": 1,
        "name": "Organic Tomatoes",
        "category": {
            "id": 1,
            "name": "Vegetables"
        },
        "default_unit": "pieces"
    },
    "location": {
        "id": 1,
        "name": "Refrigerator",
        "household": 1
    },
    "current_quantity": "5.00",
    "unit": "pieces",
    "purchase_date": "2024-01-15",
    "expiration_date": "2024-01-22",
    "purchase_price": "4.99",
    "minimum_threshold": "2.00",
    "notes": "",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

### Create Inventory Item

**Endpoint:** `POST /api/inventory/`

**Request Body:**
```json
{
    "product": 1,
    "location": 1,
    "current_quantity": "5.00",
    "unit": "pieces",
    "purchase_date": "2024-01-15",
    "expiration_date": "2024-01-22",
    "purchase_price": "4.99",
    "minimum_threshold": "2.00",
    "notes": "Bought from farmers market"
}
```

**Response:** `201 Created` with the created item details.

### Update Inventory Item

**Endpoint:** `PATCH /api/inventory/{id}/`

**Request Body:** (partial update)
```json
{
    "current_quantity": "3.00",
    "notes": "Used 2 pieces for dinner"
}
```

**Response:** `200 OK` with updated item details.

### Delete Inventory Item

**Endpoint:** `DELETE /api/inventory/{id}/`

**Response:** `204 No Content`

### Search Products

**Endpoint:** `GET /api/inventory/search-products/`

**Parameters:**
- `q`: Search query

**Response:**
```json
{
    "results": [
        {
            "id": 1,
            "name": "Organic Tomatoes",
            "category": {
                "id": 1,
                "name": "Vegetables"
            },
            "default_unit": "pieces"
        }
    ]
}
```

### Barcode Lookup

**Endpoint:** `GET /api/inventory/barcode-lookup/`

**Parameters:**
- `barcode`: Barcode number

**Response:**
```json
{
    "product": {
        "id": 1,
        "name": "Organic Tomatoes",
        "category": {
            "id": 1,
            "name": "Vegetables"
        },
        "default_unit": "pieces"
    },
    "barcode": "1234567890123",
    "barcode_type": "EAN13"
}
```

### Inventory Statistics

**Endpoint:** `GET /api/inventory/statistics/`

**Response:**
```json
{
    "total_items": 45,
    "total_value": "234.67",
    "expiring_soon": 3,
    "expired": 1,
    "low_stock": 5,
    "categories": {
        "Vegetables": 12,
        "Dairy": 8,
        "Meat": 6
    }
}
```

## Recipe API

### List Recipes

**Endpoint:** `GET /api/recipes/`

**Parameters:**
- `search`: Search by name or ingredients
- `category`: Filter by category ID
- `difficulty`: Filter by difficulty (easy, medium, hard)
- `max_prep_time`: Maximum prep time in minutes
- `max_cook_time`: Maximum cook time in minutes

**Response:**
```json
{
    "count": 15,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Tomato Basil Pasta",
            "slug": "tomato-basil-pasta",
            "description": "A simple and delicious pasta dish",
            "category": {
                "id": 1,
                "name": "Main Course"
            },
            "created_by": {
                "id": 1,
                "username": "chef_mario"
            },
            "servings": 4,
            "prep_time": 15,
            "cook_time": 20,
            "difficulty": "easy",
            "is_public": true,
            "image": "https://example.com/media/recipes/pasta.jpg",
            "created_at": "2024-01-10T12:00:00Z"
        }
    ]
}
```

### Get Recipe

**Endpoint:** `GET /api/recipes/{id}/`

**Response:**
```json
{
    "id": 1,
    "name": "Tomato Basil Pasta",
    "slug": "tomato-basil-pasta",
    "description": "A simple and delicious pasta dish",
    "category": {
        "id": 1,
        "name": "Main Course"
    },
    "created_by": {
        "id": 1,
        "username": "chef_mario"
    },
    "servings": 4,
    "prep_time": 15,
    "cook_time": 20,
    "difficulty": "easy",
    "instructions": "1. Boil water for pasta...",
    "is_public": true,
    "image": "https://example.com/media/recipes/pasta.jpg",
    "nutrition_info": {
        "calories": 450,
        "protein": "12g",
        "carbs": "65g",
        "fat": "18g"
    },
    "created_at": "2024-01-10T12:00:00Z",
    "updated_at": "2024-01-10T12:00:00Z"
}
```

### Create Recipe

**Endpoint:** `POST /api/recipes/`

**Request Body:**
```json
{
    "name": "Tomato Basil Pasta",
    "description": "A simple and delicious pasta dish",
    "category": 1,
    "servings": 4,
    "prep_time": 15,
    "cook_time": 20,
    "difficulty": "easy",
    "instructions": "1. Boil water for pasta...",
    "is_public": true
}
```

**Response:** `201 Created` with the created recipe details.

### Update Recipe

**Endpoint:** `PATCH /api/recipes/{id}/`

**Request Body:** (partial update)
```json
{
    "servings": 6,
    "instructions": "Updated instructions..."
}
```

**Response:** `200 OK` with updated recipe details.

### Delete Recipe

**Endpoint:** `DELETE /api/recipes/{id}/`

**Response:** `204 No Content`

### Get Recipe Ingredients

**Endpoint:** `GET /api/recipes/{id}/ingredients/`

**Response:**
```json
[
    {
        "id": 1,
        "product": {
            "id": 1,
            "name": "Pasta",
            "category": {
                "id": 2,
                "name": "Grains"
            }
        },
        "quantity": "400.00",
        "unit": "grams",
        "notes": "Any pasta shape works"
    },
    {
        "id": 2,
        "product": {
            "id": 3,
            "name": "Tomatoes",
            "category": {
                "id": 1,
                "name": "Vegetables"
            }
        },
        "quantity": "3.00",
        "unit": "pieces",
        "notes": "Fresh tomatoes preferred"
    }
]
```

### Recipe Matching

**Endpoint:** `GET /api/recipes/matching/`

**Description:** Find recipes that can be made with current inventory.

**Parameters:**
- `threshold`: Minimum percentage of ingredients available (default: 80)

**Response:**
```json
{
    "results": [
        {
            "recipe": {
                "id": 1,
                "name": "Tomato Basil Pasta",
                "slug": "tomato-basil-pasta"
            },
            "match_percentage": 100,
            "available_ingredients": 3,
            "total_ingredients": 3,
            "missing_ingredients": []
        },
        {
            "recipe": {
                "id": 2,
                "name": "Garden Salad",
                "slug": "garden-salad"
            },
            "match_percentage": 75,
            "available_ingredients": 3,
            "total_ingredients": 4,
            "missing_ingredients": [
                {
                    "product": "Lettuce",
                    "quantity": "1.00",
                    "unit": "head"
                }
            ]
        }
    ]
}
```

### Search Recipes

**Endpoint:** `GET /api/recipes/search/`

**Parameters:**
- `q`: Search query
- `ingredients`: Comma-separated list of ingredient names

**Response:**
```json
{
    "results": [
        {
            "id": 1,
            "name": "Tomato Basil Pasta",
            "slug": "tomato-basil-pasta",
            "description": "A simple and delicious pasta dish",
            "match_score": 0.95
        }
    ]
}
```

## Shopping API

### List Shopping Lists

**Endpoint:** `GET /api/shopping/lists/`

**Parameters:**
- `status`: Filter by status (active, completed, archived)
- `store`: Filter by store ID

**Response:**
```json
{
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "name": "Weekly Groceries",
            "status": "active",
            "created_by": {
                "id": 1,
                "username": "user1"
            },
            "store": {
                "id": 1,
                "name": "Local Supermarket",
                "store_type": "grocery"
            },
            "budget_limit": "100.00",
            "total_estimated_cost": "85.50",
            "items_count": 12,
            "completed_items_count": 8,
            "created_at": "2024-01-15T09:00:00Z",
            "updated_at": "2024-01-15T14:30:00Z"
        }
    ]
}
```

### Get Shopping List

**Endpoint:** `GET /api/shopping/lists/{id}/`

**Response:**
```json
{
    "id": 1,
    "name": "Weekly Groceries",
    "status": "active",
    "created_by": {
        "id": 1,
        "username": "user1"
    },
    "household": {
        "id": 1,
        "name": "Smith Family"
    },
    "store": {
        "id": 1,
        "name": "Local Supermarket",
        "store_type": "grocery"
    },
    "budget_limit": "100.00",
    "total_estimated_cost": "85.50",
    "notes": "Don't forget the milk!",
    "shared_with": [
        {
            "user": {
                "id": 2,
                "username": "spouse"
            },
            "permission": "edit"
        }
    ],
    "created_at": "2024-01-15T09:00:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
}
```

### Create Shopping List

**Endpoint:** `POST /api/shopping/lists/`

**Request Body:**
```json
{
    "name": "Weekly Groceries",
    "store": 1,
    "budget_limit": "100.00",
    "notes": "Don't forget the milk!"
}
```

**Response:** `201 Created` with the created list details.

### Update Shopping List

**Endpoint:** `PATCH /api/shopping/lists/{id}/`

**Request Body:** (partial update)
```json
{
    "name": "Updated List Name",
    "budget_limit": "120.00"
}
```

**Response:** `200 OK` with updated list details.

### Delete Shopping List

**Endpoint:** `DELETE /api/shopping/lists/{id}/`

**Response:** `204 No Content`

### List Shopping Items

**Endpoint:** `GET /api/shopping/lists/{list_id}/items/`

**Response:**
```json
[
    {
        "id": 1,
        "product": {
            "id": 1,
            "name": "Milk",
            "category": {
                "id": 3,
                "name": "Dairy"
            }
        },
        "name": "Organic Milk",
        "quantity": "2.00",
        "unit": "liters",
        "estimated_price": "6.50",
        "actual_price": "6.99",
        "is_purchased": false,
        "priority": "normal",
        "notes": "2% fat",
        "created_at": "2024-01-15T09:15:00Z"
    }
]
```

### Add Item to Shopping List

**Endpoint:** `POST /api/shopping/lists/{list_id}/items/`

**Request Body:**
```json
{
    "product": 1,
    "name": "Organic Milk",
    "quantity": "2.00",
    "unit": "liters",
    "estimated_price": "6.50",
    "priority": "normal",
    "notes": "2% fat"
}
```

**Response:** `201 Created` with the created item details.

### Toggle Item Purchased Status

**Endpoint:** `PATCH /api/shopping/items/{item_id}/toggle/`

**Request Body:**
```json
{
    "is_purchased": true,
    "actual_price": "6.99"
}
```

**Response:** `200 OK` with updated item details.

### Generate List from Depleted Items

**Endpoint:** `POST /api/shopping/generate-from-depleted/`

**Request Body:**
```json
{
    "name": "Restock List",
    "threshold_days": 7,
    "include_expired": true
}
```

**Description:** Creates a shopping list based on items that are low in stock or expiring soon.

**Response:** `201 Created` with the created list details.

### Share Shopping List

**Endpoint:** `POST /api/shopping/lists/{list_id}/share/`

**Request Body:**
```json
{
    "email": "friend@example.com",
    "permission": "view"
}
```

**Permissions:**
- `view`: Can view the list
- `edit`: Can view and modify the list

**Response:** `201 Created`

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful GET, PATCH requests
- `201 Created`: Successful POST requests
- `204 No Content`: Successful DELETE requests
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `405 Method Not Allowed`: HTTP method not supported
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
    "error": {
        "code": "validation_error",
        "message": "The request data is invalid",
        "details": {
            "current_quantity": ["This field is required"],
            "expiration_date": ["Date format should be YYYY-MM-DD"]
        }
    }
}
```

### Common Error Codes

- `authentication_failed`: Invalid or missing authentication token
- `permission_denied`: Insufficient permissions for the requested action
- `validation_error`: Request data validation failed
- `not_found`: Requested resource does not exist
- `rate_limit_exceeded`: Too many requests in a short period

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Authenticated users**: 1000 requests per hour
- **Anonymous users**: 100 requests per hour

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

When rate limit is exceeded, a `429 Too Many Requests` response is returned with a `Retry-After` header.

## Examples

### Adding an Inventory Item with Barcode

```bash
# 1. Look up product by barcode
curl -X GET "https://api.kitchentory.com/api/inventory/barcode-lookup/?barcode=1234567890123" \
  -H "Authorization: Token your_token_here"

# 2. Add the item to inventory
curl -X POST "https://api.kitchentory.com/api/inventory/" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "product": 1,
    "location": 1,
    "current_quantity": "3.00",
    "unit": "pieces",
    "purchase_date": "2024-01-15",
    "expiration_date": "2024-01-22",
    "purchase_price": "4.99"
  }'
```

### Finding Recipes You Can Make

```bash
curl -X GET "https://api.kitchentory.com/api/recipes/matching/?threshold=80" \
  -H "Authorization: Token your_token_here"
```

### Creating a Shopping List from Low Stock

```bash
curl -X POST "https://api.kitchentory.com/api/shopping/generate-from-depleted/" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Restock List",
    "threshold_days": 7,
    "include_expired": true
  }'
```

### Complete Shopping Workflow

```bash
# 1. Create shopping list
curl -X POST "https://api.kitchentory.com/api/shopping/lists/" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekend Shopping",
    "store": 1,
    "budget_limit": "50.00"
  }'

# 2. Add items to list
curl -X POST "https://api.kitchentory.com/api/shopping/lists/1/items/" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "product": 1,
    "name": "Organic Apples",
    "quantity": "2.00",
    "unit": "kg",
    "estimated_price": "8.00"
  }'

# 3. Mark item as purchased
curl -X PATCH "https://api.kitchentory.com/api/shopping/items/1/toggle/" \
  -H "Authorization: Token your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "is_purchased": true,
    "actual_price": "7.50"
  }'
```

## SDK and Libraries

Official SDKs are available for:

- **Python**: `pip install kitchentory-api`
- **JavaScript/Node.js**: `npm install kitchentory-api`
- **iOS**: Available via Swift Package Manager
- **Android**: Available via Maven Central

### Python SDK Example

```python
from kitchentory_api import KitchentoryClient

client = KitchentoryClient(token='your_token_here')

# Get inventory items
items = client.inventory.list(expired=False)

# Create shopping list
shopping_list = client.shopping.create_list({
    'name': 'Weekly Groceries',
    'budget_limit': '100.00'
})

# Find matching recipes
recipes = client.recipes.find_matching(threshold=80)
```

## Support

For API support, please contact:

- **Email**: api-support@kitchentory.com
- **Documentation**: https://docs.kitchentory.com/api
- **Status Page**: https://status.kitchentory.com
- **GitHub Issues**: https://github.com/kitchentory/api-issues

## Changelog

### v1.2.0 (2024-01-15)
- Added recipe matching endpoint
- Improved barcode lookup accuracy
- Added shopping list sharing functionality

### v1.1.0 (2024-01-01)
- Added inventory statistics endpoint
- Enhanced search capabilities
- Added rate limiting headers

### v1.0.0 (2023-12-01)
- Initial API release
- Basic CRUD operations for inventory, recipes, and shopping lists
- Token-based authentication