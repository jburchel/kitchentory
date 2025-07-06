# Kitchentory Integrations

This app handles various integrations for importing inventory data into Kitchentory.

## Features

### ✅ CSV/Excel Import System

A comprehensive system for importing inventory data from CSV and Excel files.

#### Features:
- **File Support**: CSV (.csv), Excel (.xlsx, .xls)
- **Smart Column Mapping**: Auto-detects columns and suggests mappings
- **Data Validation**: Validates quantities, prices, dates, and units
- **Preview System**: Shows preview with error detection before import
- **Progress Tracking**: Real-time import progress with detailed results
- **Error Reporting**: Detailed error messages for failed imports
- **Data Normalization**: Automatically cleans and standardizes data

#### API Endpoints:
- `GET /api/integrations/csv/sample/` - Download sample CSV
- `POST /api/integrations/csv/preview/` - Preview import data
- `POST /api/integrations/csv/process/` - Process import
- `POST /api/integrations/csv/validate-mapping/` - Validate column mapping
- `GET /api/integrations/imports/` - Import history
- `GET /api/integrations/imports/{id}/` - Import status
- `DELETE /api/integrations/imports/{id}/cancel/` - Cancel import
- `GET /api/integrations/imports/{id}/errors/` - Import errors

#### Web Interface:
- `/integrations/import/` - Main import interface
- `/integrations/import/history/` - Import history
- `/integrations/import/{id}/` - Import details

#### Usage Example:

```python
from integrations.csv_import import CSVImportService

# Initialize service
service = CSVImportService(household=household, user=user)

# Validate file
is_valid, message = service.validate_file(uploaded_file)

# Preview import
preview = service.preview_import(uploaded_file, mapping)

# Process import
import_job = service.process_import(uploaded_file, mapping)
```

#### Sample CSV Format:

```csv
name,brand,quantity,unit,price,category,location,expiration_date,notes
Organic Bananas,Fresh Market,2,lb,3.99,Produce,Fridge,2024-01-15,Ripe and sweet
Whole Milk,Dairy Farm,1,gal,4.49,Dairy,Fridge,2024-01-10,
Chicken Breast,Premium Poultry,2.5,lb,12.99,Meat,Freezer,2024-02-01,Boneless skinless
```

#### Data Mapping:

The system supports mapping CSV columns to these inventory fields:

- **name** (required) - Product name
- **brand** - Brand/manufacturer
- **quantity** - Quantity amount
- **unit** - Unit of measurement (oz, lb, gal, count, etc.)
- **price** - Price paid
- **category** - Product category
- **location** - Storage location (fridge, pantry, etc.)
- **expiration_date** - Expiration date
- **notes** - Additional notes
- **barcode** - Product barcode/UPC

#### Validation Rules:

1. **Product Name**: Required, max 200 characters
2. **Quantity**: Must be positive number, defaults to 1
3. **Price**: Must be positive number or null
4. **Unit**: Normalized to standard units (oz, lb, gal, etc.)
5. **Date**: Supports multiple date formats
6. **Barcode**: Optional, used for product matching

#### Error Handling:

- Invalid file formats are rejected
- Large files (>10MB) are rejected
- Too many rows (>5000) are rejected
- Detailed error reporting per row
- Graceful handling of malformed data
- Progress tracking with partial success

### ✅ Email Receipt Parsing

Comprehensive system for parsing grocery receipts from email forwarding with AI-powered parsing and multi-store support.

#### Features:
- **Email Webhook Integration**: Support for SendGrid, Mailgun, Postmark, and generic webhooks
- **Store-Specific Parsers**: Dedicated parsers for Instacart, Amazon Fresh, Walmart, Target, Kroger, Safeway, Costco, and Whole Foods
- **Intelligent Text Parsing**: Advanced regex patterns and confidence scoring for accurate item extraction
- **Auto-Processing**: High-confidence receipts can be automatically added to inventory
- **Manual Review Interface**: Review and edit parsed items before importing
- **Error Handling**: Robust error reporting and fallback mechanisms
- **Security**: Webhook signature verification for supported services

#### Supported Stores:

| Store | Status | Confidence | Features |
|-------|--------|------------|----------|
| Instacart | ✅ Full | 95% | Order ID, totals, item parsing |
| Amazon Fresh | ✅ Full | 90% | Date extraction, item detection |
| Walmart | ✅ Full | 85% | Receipt parsing, price extraction |
| Target | 🔶 Beta | 80% | Basic parsing, totals |
| Kroger | 🔶 Beta | 75% | Item detection, family stores |
| Safeway | 🔶 Beta | 75% | Vons, Pavilions support |
| Costco | 🔶 Beta | 70% | Item numbers, bulk pricing |
| Whole Foods | 🔶 Beta | 80% | Amazon integration |
| Generic Store | 🔶 Basic | 60% | Fallback parsing |

#### API Endpoints:
- `POST /api/integrations/webhooks/sendgrid/` - SendGrid webhook
- `POST /api/integrations/webhooks/mailgun/` - Mailgun webhook  
- `POST /api/integrations/webhooks/postmark/` - Postmark webhook
- `POST /api/integrations/webhooks/generic/` - Generic webhook
- `POST /api/integrations/receipts/upload/` - Manual email upload
- `GET /api/integrations/receipts/` - Receipt import history

#### Web Interface:
- `/integrations/receipts/review/{id}/` - Review parsed receipt
- `/integrations/email-setup/` - Setup guide for email forwarding
- `/integrations/manual-upload/` - Manual email content upload

#### Usage Example:

```python
from integrations.enhanced_receipt_parser import EnhancedReceiptParser

# Initialize parser
parser = EnhancedReceiptParser()

# Parse email receipt
email_data = {
    'sender': 'receipts@instacart.com',
    'subject': 'Your Instacart order has been delivered',
    'body': '... receipt content ...'
}

parsed_receipt = parser.parse_email_receipt(email_data)

print(f"Store: {parsed_receipt.store_name}")
print(f"Items found: {len(parsed_receipt.items)}")
print(f"Confidence: {parsed_receipt.confidence_score:.1%}")
```

#### Email Setup Instructions:

1. **SendGrid Setup**:
   - Configure inbound parse webhook
   - Point to `/api/integrations/webhooks/sendgrid/`
   - Set up DNS routing

2. **Mailgun Setup**:
   - Create route for receipt emails
   - Forward to `/api/integrations/webhooks/mailgun/`
   - Configure signature verification

3. **Gmail Forwarding**:
   - Create filters for store emails
   - Forward to processing address
   - Use manual upload for testing

4. **Manual Upload**:
   - Copy/paste email content
   - Test parsing before automation
   - Review confidence scores

#### Parsing Accuracy:

The system uses multiple techniques for accurate parsing:
- **Store Detection**: Email sender and content analysis
- **Item Extraction**: Store-specific regex patterns
- **Price Parsing**: Currency and number extraction
- **Quantity Detection**: Units and measurement parsing
- **Category Inference**: Smart categorization based on product names
- **Confidence Scoring**: Per-item and overall confidence metrics

#### Auto-Processing Rules:

High-confidence receipts (>80%) with no parsing errors are automatically processed. Lower confidence receipts require manual review. You can adjust these thresholds in the admin interface.

#### Error Handling:

- Malformed emails are logged with detailed error messages
- Partial parsing continues even if some items fail
- Duplicate detection prevents re-importing same receipts
- Backup parsers handle edge cases and unknown formats

### 🚧 Direct Store API Integration (Planned)

Direct integration with grocery store APIs.

#### Research Status:
- Investigating available APIs
- OAuth implementation planning
- Purchase history sync design

## Models

### ImportJob
Tracks import operations from various sources.

### ImportSource
- `EMAIL_RECEIPT` - Email receipt
- `CSV_UPLOAD` - CSV/Excel upload
- `BROWSER_EXTENSION` - Browser extension
- `STORE_API` - Store API

### ImportStatus
- `PENDING` - Awaiting review
- `PROCESSING` - Being processed
- `COMPLETED` - Successfully completed
- `FAILED` - Failed with errors
- `CANCELLED` - Cancelled by user

### ParsedReceiptItem
Individual items parsed from imports.

## Installation

1. **Add to INSTALLED_APPS**:
```python
INSTALLED_APPS = [
    # ...
    'integrations',
]
```

2. **Include URLs**:
```python
urlpatterns = [
    # ...
    path('integrations/', include('integrations.urls')),
    path('api/integrations/', include('integrations.api_urls')),
]
```

3. **Install Dependencies**:
```bash
pip install openpyxl
```

4. **Run Migrations**:
```bash
python manage.py makemigrations integrations
python manage.py migrate
```

## Configuration

### File Upload Limits

```python
# settings.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
```

### CSV Import Settings

```python
# Custom settings in csv_import.py
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ROWS = 5000  # Maximum rows per import
SUPPORTED_EXTENSIONS = ['.csv', '.xlsx', '.xls']
```

## Testing

### Sample Data

Use the sample CSV endpoint to get properly formatted test data:

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
     https://your-domain.com/api/integrations/csv/sample/ \
     -o sample.csv
```

### Testing Flow

1. **Upload Sample**: Use sample CSV for testing
2. **Test Mapping**: Try different column configurations
3. **Test Validation**: Upload files with errors
4. **Test Progress**: Monitor import progress
5. **Verify Results**: Check created inventory items

## Deployment

### Production Considerations

1. **File Storage**: Configure proper file storage backend
2. **Background Tasks**: Consider using Celery for large imports
3. **Rate Limiting**: Implement rate limiting for API endpoints
4. **Monitoring**: Set up monitoring for import failures
5. **Cleanup**: Regular cleanup of old import jobs

### Security

1. **File Validation**: Strict file type and size validation
2. **Input Sanitization**: All user input is sanitized
3. **Access Control**: Household-based access restrictions
4. **Error Handling**: Safe error messages without data exposure

## Future Enhancements

1. **Background Processing**: Use Celery for large imports
2. **Advanced Mapping**: AI-powered column detection
3. **Duplicate Detection**: Smart duplicate handling
4. **Batch Operations**: Bulk edit imported items
5. **Import Templates**: Save mapping configurations
6. **Data Enrichment**: Auto-enrich products from APIs
7. **Import Scheduling**: Scheduled imports from external sources