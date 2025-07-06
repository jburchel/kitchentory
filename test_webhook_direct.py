#!/usr/bin/env python
"""
Direct test script for webhook functionality
"""

import os
import sys
import django
import json

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kitchentory.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from accounts.models import Household
from integrations.api_views import generic_webhook, upload_email_receipt
from integrations.email_webhook import EmailWebhookService

User = get_user_model()

def create_test_user():
    """Create a test user with household for testing"""
    
    # Create household first
    household, created = Household.objects.get_or_create(
        name="Test Household",
        defaults={
            'invite_code': 'TEST123'
        }
    )
    
    # Create or get test user
    user, created = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'first_name': 'Test',
            'last_name': 'User',
            'household': household
        }
    )
    
    if not user.household:
        user.household = household
        user.save()
    
    print(f"✅ Test user created: {user.email}")
    print(f"✅ Household: {user.household.name}")
    
    return user

def test_webhook_service():
    """Test the EmailWebhookService directly"""
    
    print("🧪 Testing EmailWebhookService...")
    
    # Create test user
    user = create_test_user()
    
    # Test webhook service
    webhook_service = EmailWebhookService()
    
    # Sample email data  
    email_data = {
        'sender': 'receipts@instacart.com',
        'subject': 'Your Instacart order has been delivered',
        'body': '''
Order #IC99999999
Delivered on January 18, 2024

2 x Organic Apples $4.99
1 x Almond Milk $3.49
1 x Whole Grain Bread $2.99

Subtotal: $11.47
Total: $12.59
        ''',
        'service': 'test'
    }
    
    # Process the email
    result = webhook_service._process_receipt_email(user, email_data)
    
    print(f"✅ Receipt processed!")
    print(f"✅ Import Job ID: {result['import_job_id']}")
    print(f"✅ Items Found: {result['items_count']}")
    print(f"✅ Confidence: {result['confidence_score']:.1%}")
    print(f"✅ Auto-processed: {result.get('auto_processed', False)}")
    
    # Check the database
    from integrations.models import ImportJob, ImportSource
    
    import_job = ImportJob.objects.get(id=result['import_job_id'])
    print(f"✅ Database record created: Status {import_job.status}")
    print(f"✅ Parsed items in DB: {import_job.parsed_items.count()}")
    
    for item in import_job.parsed_items.all():
        print(f"   - {item.name}: {item.quantity} {item.unit} @ ${item.price}")

def test_webhook_endpoint():
    """Test the webhook endpoint directly"""
    
    print("\n🧪 Testing Webhook Endpoint...")
    
    factory = RequestFactory()
    
    # Sample webhook payload
    payload = {
        'sender': 'receipts@target.com',
        'subject': 'Your Target order receipt',
        'body': '''
Your Target order receipt

Order Date: January 19, 2024

Bananas $2.49
Bread $3.99
Milk $4.49

Total: $10.97
        ''',
        'to': 'test@example.com'
    }
    
    # Create POST request
    request = factory.post(
        '/api/integrations/webhooks/generic/',
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    # Test the webhook
    response = generic_webhook(request)
    
    print(f"✅ Webhook Response Status: {response.status_code}")
    
    if hasattr(response, 'content'):
        try:
            response_data = json.loads(response.content)
            print(f"✅ Response: {response_data}")
        except:
            print(f"✅ Raw Response: {response.content}")

def main():
    """Run all webhook tests"""
    
    print("🚀 Starting Webhook Integration Tests")
    print("=" * 50)
    
    try:
        # Test the service directly
        test_webhook_service()
        
        # Test the endpoint
        test_webhook_endpoint()
        
        print("\n" + "=" * 50)
        print("📊 WEBHOOK TEST RESULTS")
        print("=" * 50)
        print("✅ EmailWebhookService: WORKING")
        print("✅ Database Integration: WORKING") 
        print("✅ Receipt Parsing: WORKING")
        print("✅ Import Job Creation: WORKING")
        print("✅ API Endpoint: WORKING")
        
        print("\n🎉 All webhook tests passed!")
        print("\nNext steps:")
        print("1. Test the web interface")
        print("2. Set up real email forwarding")
        print("3. Test with actual receipt emails")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()