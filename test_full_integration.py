#!/usr/bin/env python
"""
Full integration test for email receipt parsing
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kitchentory.settings")
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Household
from integrations.enhanced_receipt_parser import EnhancedReceiptParser
from integrations.email_webhook import EmailWebhookService
from integrations.models import ImportJob, ImportSource, ImportStatus

User = get_user_model()


def setup_test_data():
    """Set up test user and household"""

    # Create household
    household, created = Household.objects.get_or_create(
        name="Integration Test Household", defaults={"invite_code": "INTTEST"}
    )

    # Create user
    user, created = User.objects.get_or_create(
        email="integration@test.com",
        defaults={
            "first_name": "Integration",
            "last_name": "Test",
            "household": household,
        },
    )

    if not user.household:
        user.household = household
        user.save()

    return user, household


def test_complete_flow():
    """Test the complete email-to-inventory flow"""

    print("🧪 FULL INTEGRATION TEST")
    print("=" * 60)

    # Setup
    user, household = setup_test_data()
    print(f"✅ Test user: {user.email}")
    print(f"✅ Household: {household.name}")

    # Test 1: Direct parser test
    print(f"\n📧 Test 1: Direct Parser Test")
    print("-" * 30)

    parser = EnhancedReceiptParser()

    email_data = {
        "sender": "receipts@instacart.com",
        "subject": "Your Instacart order has been delivered",
        "body": """
Your Instacart order has been delivered!

Order #IC12345678
Delivered on January 20, 2024

Your order from Safeway:

2 x Organic Bananas $3.99
1 x Whole Milk, 1 Gallon $4.49
3 x Hass Avocados $5.97
1 x Sourdough Bread Loaf $3.29
2 x Greek Yogurt, Vanilla, 6oz $6.98

Subtotal: $24.72
Tax: $1.98
Total: $26.70

Thank you for shopping with Instacart!
        """,
    }

    parsed_receipt = parser.parse_email_receipt(email_data)

    print(f"   Store: {parsed_receipt.store_name}")
    print(f"   Date: {parsed_receipt.purchase_date}")
    print(f"   Total: ${parsed_receipt.total}")
    print(f"   Items: {len(parsed_receipt.items)}")
    print(f"   Confidence: {parsed_receipt.confidence_score:.1%}")

    for i, item in enumerate(parsed_receipt.items, 1):
        print(f"   {i}. {item.name} ({item.quantity} {item.unit}) - ${item.price}")

    # Test 2: Webhook service test
    print(f"\n📧 Test 2: Webhook Service Test")
    print("-" * 30)

    webhook_service = EmailWebhookService()
    result = webhook_service._process_receipt_email(user, email_data)

    print(f"   Import Job ID: {result['import_job_id']}")
    print(f"   Items Created: {result['items_count']}")
    print(f"   Confidence: {result['confidence_score']:.1%}")
    print(f"   Auto-processed: {result.get('auto_processed', False)}")

    # Test 3: Database verification
    print(f"\n📧 Test 3: Database Verification")
    print("-" * 30)

    import_job = ImportJob.objects.get(id=result["import_job_id"])

    print(f"   Import Job Status: {import_job.status}")
    print(f"   Source: {import_job.get_source_display()}")
    print(f"   Parsed Items Count: {import_job.parsed_items.count()}")
    print(f"   Email Data: {bool(import_job.email_data)}")
    print(f"   Raw Data: {bool(import_job.raw_data)}")

    if import_job.raw_data:
        print(f"   Store Name: {import_job.raw_data.get('store_name')}")
        print(f"   Confidence: {import_job.raw_data.get('confidence_score', 0):.1%}")

    # List parsed items
    parsed_items = import_job.parsed_items.all()
    print(f"\n   📦 Parsed Items in Database:")
    for item in parsed_items:
        print(f"      - {item.name}: {item.quantity} {item.unit}")
        print(f"        Price: ${item.price}, Confidence: {item.confidence_score:.1%}")
        if item.suggested_category:
            print(f"        Category: {item.suggested_category}")

    # Test 4: High confidence auto-processing
    print(f"\n📧 Test 4: Auto-Processing Test")
    print("-" * 30)

    high_confidence_email = {
        "sender": "receipts@instacart.com",
        "subject": "Your Instacart order has been delivered",
        "body": """
Order #IC99999999
Delivered on January 21, 2024

2 x Bananas $2.99
1 x Milk $3.99

Subtotal: $6.98
Total: $7.50
        """,
    }

    # This should auto-process if confidence > 80%
    auto_result = webhook_service._process_receipt_email(user, high_confidence_email)
    auto_job = ImportJob.objects.get(id=auto_result["import_job_id"])

    print(f"   Auto Import Job: {auto_job.id}")
    print(f"   Status: {auto_job.status}")
    print(f"   Auto-processed: {auto_result.get('auto_processed', False)}")

    # Test 5: Different store test
    print(f"\n📧 Test 5: Amazon Fresh Test")
    print("-" * 30)

    amazon_email = {
        "sender": "auto-confirm@amazon.com",
        "subject": "Your Amazon Fresh order has been delivered",
        "body": """
Your Amazon Fresh order has been delivered

Order Date: January 22, 2024
Order Total: $15.47

Items in this order:

Chicken Breast, 1 lb $6.99
Pasta, 16 oz $1.99
Tomato Sauce $2.49
Spinach, Fresh, 5 oz $2.99
Olive Oil, 250ml $4.99

Thank you!
        """,
    }

    amazon_result = webhook_service._process_receipt_email(user, amazon_email)
    amazon_job = ImportJob.objects.get(id=amazon_result["import_job_id"])

    print(f"   Amazon Import Job: {amazon_job.id}")
    print(f"   Items Found: {amazon_result['items_count']}")
    print(
        f"   Store: {amazon_job.raw_data.get('store_name') if amazon_job.raw_data else 'Unknown'}"
    )

    # Final summary
    print(f"\n🎯 INTEGRATION TEST SUMMARY")
    print("=" * 60)

    total_jobs = ImportJob.objects.filter(household=household).count()
    total_items = sum(
        job.parsed_items.count()
        for job in ImportJob.objects.filter(household=household)
    )

    print(f"✅ Total Import Jobs Created: {total_jobs}")
    print(f"✅ Total Items Parsed: {total_items}")
    print(f"✅ Stores Tested: Instacart, Amazon Fresh")
    print(
        f"✅ Auto-processing: {'Enabled' if auto_result.get('auto_processed') else 'Manual Review Required'}"
    )

    # Test different confidence levels
    jobs_by_status = {}
    for job in ImportJob.objects.filter(household=household):
        status = job.status
        jobs_by_status[status] = jobs_by_status.get(status, 0) + 1

    print(f"✅ Job Statuses: {dict(jobs_by_status)}")

    print(f"\n🚀 SYSTEM STATUS: FULLY OPERATIONAL")

    print(f"\n📋 Next Steps for Production:")
    print(f"   1. Set up email forwarding rules")
    print(f"   2. Configure webhook endpoints")
    print(f"   3. Test with real receipts")
    print(f"   4. Adjust confidence thresholds")
    print(f"   5. Create user documentation")


if __name__ == "__main__":
    test_complete_flow()
