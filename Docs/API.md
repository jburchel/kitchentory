# Kitchentory API Documentation

## Base URL
```
/api/inventory/
```

## Authentication
All API endpoints require authentication. The API uses Django session authentication by default.

## Endpoints

### Categories

#### List Categories
- **GET** `/api/inventory/categories/`
- Returns all categories with item counts for the user's household
- Supports search: `?search=produce`
- Supports ordering: `?ordering=name` or `?ordering=-item_count`

#### Get Category
- **GET** `/api/inventory/categories/{id}/`
- Returns details for a specific category

### Products

#### List Products
- **GET** `/api/inventory/products/`
- Returns all products
- Supports filters: `?category={id}`, `?default_unit=kg`
- Supports search: `?search=apple`
- Supports ordering: `?ordering=name`

#### Search Products
- **GET** `/api/inventory/products/search/?q={query}`
- Returns up to 10 products matching the search query
- Searches name, brand, and barcode fields

#### Lookup by Barcode
- **GET** `/api/inventory/products/by_barcode/?barcode={barcode}`
- Returns product with the specified barcode
- Returns 404 if not found

#### Get Product
- **GET** `/api/inventory/products/{id}/`
- Returns details for a specific product

### Storage Locations

#### List Locations
- **GET** `/api/inventory/locations/`
- Returns storage locations for the user's household
- Supports search: `?search=fridge`
- Supports ordering: `?ordering=name`

#### Create Location
- **POST** `/api/inventory/locations/`
```json
{
  "name": "Main Fridge",
  "location_type": "fridge",
  "temperature": 4.0,
  "notes": "Main refrigerator in kitchen"
}
```

#### Update Location
- **PUT/PATCH** `/api/inventory/locations/{id}/`
- Update an existing storage location

#### Delete Location
- **DELETE** `/api/inventory/locations/{id}/`
- Delete a storage location (only if it has no items)

### Inventory Items

#### List Items
- **GET** `/api/inventory/items/`
- Returns inventory items for the user's household
- Supports filters: 
  - `?product__category={id}` - Filter by category
  - `?location={id}` - Filter by location
  - `?unit=kg` - Filter by unit
  - `?is_expired=true` - Filter expired items
  - `?expiring_soon=7` - Items expiring in next 7 days
  - `?expired=true` - Only expired items
- Supports search: `?search=apple`
- Supports ordering: `?ordering=-created_at`, `?ordering=expiration_date`, `?ordering=product__name`

#### Create Item
- **POST** `/api/inventory/items/`
```json
{
  "product_id": "uuid-here",
  "quantity": 2.5,
  "unit": "kg",
  "location_id": "uuid-here",
  "expiration_date": "2024-01-15",
  "purchase_date": "2024-01-01",
  "price": 5.99,
  "notes": "Fresh organic apples"
}
```

#### Quick Add Item
- **POST** `/api/inventory/items/quick_add/`
```json
{
  "name": "Red Apples",
  "brand": "Organic Farms",
  "category_id": "uuid-here",
  "quantity": 5,
  "unit": "count",
  "location_id": "uuid-here",
  "days_until_expiration": 14
}
```

#### Get Item
- **GET** `/api/inventory/items/{id}/`
- Returns details for a specific inventory item

#### Update Item
- **PUT/PATCH** `/api/inventory/items/{id}/`
- Update an inventory item

#### Delete Item
- **DELETE** `/api/inventory/items/{id}/`
- Delete an inventory item

#### Consume Item
- **POST** `/api/inventory/items/{id}/consume/`
- Mark an item as consumed (deletes it)

#### Bulk Actions
- **POST** `/api/inventory/items/bulk_action/`
```json
{
  "item_ids": ["uuid1", "uuid2", "uuid3"],
  "action": "consume",
  // For update_location action:
  "location_id": "uuid-here",
  // For update_expiration action:
  "expiration_date": "2024-02-01"
}
```

Available actions:
- `consume` - Mark items as consumed (delete them)
- `delete` - Delete items
- `update_location` - Update storage location
- `update_expiration` - Update expiration date

#### Statistics
- **GET** `/api/inventory/items/stats/`
- Returns inventory statistics:
```json
{
  "total_items": 25,
  "expired_items": 2,
  "expiring_soon": 5,
  "top_categories": [
    {"product__category__name": "Produce", "count": 8},
    {"product__category__name": "Dairy", "count": 5}
  ],
  "top_locations": [
    {"location__name": "Main Fridge", "count": 12},
    {"location__name": "Pantry", "count": 8}
  ]
}
```

#### Expiring Items
- **GET** `/api/inventory/items/expiring/?days=7`
- Returns items expiring in the next N days (default: 7)

#### Expired Items
- **GET** `/api/inventory/items/expired/`
- Returns all expired items

## Response Format

### Success Responses
All successful responses return JSON data with the requested information.

### Error Responses
Error responses include an appropriate HTTP status code and error details:

```json
{
  "error": "Error message",
  "details": "Additional error information"
}
```

### Validation Errors
Field validation errors are returned in this format:
```json
{
  "field_name": ["Error message for this field"],
  "another_field": ["Another error message"]
}
```

## Pagination

List endpoints support pagination using the `page` parameter:
- `?page=1` - First page
- `?page=2` - Second page

Response includes pagination metadata:
```json
{
  "count": 100,
  "next": "http://example.com/api/inventory/items/?page=3",
  "previous": "http://example.com/api/inventory/items/?page=1",
  "results": [...]
}
```

## Rate Limiting

No rate limiting is currently implemented, but it may be added in the future.

## Examples

### Add a new item by barcode
```bash
# 1. Look up product by barcode
curl -X GET "/api/inventory/products/by_barcode/?barcode=123456789"

# 2. Add item to inventory
curl -X POST "/api/inventory/items/" \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "uuid-from-step-1",
    "quantity": 1,
    "unit": "count",
    "location_id": "fridge-location-uuid",
    "days_until_expiration": 30
  }'
```

### Get items expiring soon
```bash
curl -X GET "/api/inventory/items/expiring/?days=3"
```

### Bulk consume multiple items
```bash
curl -X POST "/api/inventory/items/bulk_action/" \
  -H "Content-Type: application/json" \
  -d '{
    "item_ids": ["uuid1", "uuid2", "uuid3"],
    "action": "consume"
  }'
```