#!/usr/bin/env python
"""
Test script for email receipt parsing functionality
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kitchentory.settings')
django.setup()

from integrations.enhanced_receipt_parser import EnhancedReceiptParser
from integrations.email_webhook import EmailWebhookService, process_raw_email
from accounts.models import User, Household

def test_instacart_receipt():
    """Test parsing an Instacart receipt"""
    
    print("🧪 Testing Instacart Receipt Parsing...")
    
    # Sample Instacart receipt email
    email_data = {
        'sender': 'receipts@instacart.com',
        'subject': 'Your Instacart order has been delivered',
        'body': '''
Your Instacart order has been delivered!

Order #IC12345678
Delivered on January 15, 2024

Your order from Whole Foods Market:

2 x Organic Bananas $3.99
1 x Whole Milk, 1 Gallon $4.49
3 x Avocados $5.97
1 x Sourdough Bread $3.29
2 x Greek Yogurt, Vanilla $6.98

Subtotal: $24.72
Tax: $1.98
Tip: $5.00
Total: $31.70

Thank you for shopping with Instacart!
        '''
    }
    
    # Parse the receipt
    parser = EnhancedReceiptParser()
    parsed_receipt = parser.parse_email_receipt(email_data)
    
    # Display results
    print(f"✅ Store: {parsed_receipt.store_name}")
    print(f"✅ Purchase Date: {parsed_receipt.purchase_date}")
    print(f"✅ Total: ${parsed_receipt.total}")
    print(f"✅ Items Found: {len(parsed_receipt.items)}")
    print(f"✅ Confidence Score: {parsed_receipt.confidence_score:.1%}")
    
    print("\n📦 Parsed Items:")
    for i, item in enumerate(parsed_receipt.items, 1):
        print(f"  {i}. {item.name}")
        print(f"     Quantity: {item.quantity} {item.unit}")
        print(f"     Price: ${item.price}")
        print(f"     Category: {item.category}")
        print(f"     Confidence: {item.confidence_score:.1%}")
        print()
    
    return parsed_receipt

def test_amazon_fresh_receipt():
    """Test parsing an Amazon Fresh receipt"""
    
    print("🧪 Testing Amazon Fresh Receipt Parsing...")
    
    email_data = {
        'sender': 'auto-confirm@amazon.com',
        'subject': 'Your Amazon Fresh order has been delivered',
        'body': '''
Your Amazon Fresh order has been delivered

Order Date: January 16, 2024
Order Total: $42.83

Items in this order:

Organic Baby Spinach, 5 oz $2.99
Chicken Breast, Boneless Skinless, 2 lbs $8.99
Roma Tomatoes, 2 lbs $3.98
Pasta Sauce, Marinara $2.49
Whole Wheat Pasta, 16 oz $1.99
Fresh Mozzarella Cheese, 8 oz $4.99
Olive Oil, Extra Virgin, 500ml $7.99

Thank you for your order!
        '''
    }
    
    parser = EnhancedReceiptParser()
    parsed_receipt = parser.parse_email_receipt(email_data)
    
    print(f"✅ Store: {parsed_receipt.store_name}")
    print(f"✅ Items Found: {len(parsed_receipt.items)}")
    print(f"✅ Confidence Score: {parsed_receipt.confidence_score:.1%}")
    
    print("\n📦 Parsed Items:")
    for i, item in enumerate(parsed_receipt.items, 1):
        print(f"  {i}. {item.name} - ${item.price} ({item.confidence_score:.1%})")
    
    return parsed_receipt

def test_walmart_receipt():
    """Test parsing a Walmart receipt"""
    
    print("🧪 Testing Walmart Receipt Parsing...")
    
    email_data = {
        'sender': 'no-reply@walmart.com',
        'subject': 'Your Walmart Grocery order is ready for pickup',
        'body': '''
Your Walmart Grocery order is ready for pickup!

Pickup Date: January 17, 2024
Order Total: $28.64

Items in your order:

Great Value Milk, 1% Lowfat, 1 Gallon $2.78
Bananas, each $0.58
Bread, White, 20 oz Loaf $1.00
Eggs, Large, Grade A, 12 Count $2.48
Cheddar Cheese, Sharp, 8 oz $2.97
Ground Beef, 93/7, 1 lb $5.97
Apples, Gala, 3 lb bag $2.98

Subtotal: $19.76
Tax: $1.58
Total: $21.34

Thank you for choosing Walmart!
        '''
    }
    
    parser = EnhancedReceiptParser()
    parsed_receipt = parser.parse_email_receipt(email_data)
    
    print(f"✅ Store: {parsed_receipt.store_name}")
    print(f"✅ Items Found: {len(parsed_receipt.items)}")
    print(f"✅ Confidence Score: {parsed_receipt.confidence_score:.1%}")
    
    return parsed_receipt

def test_webhook_processing():
    """Test webhook processing with a sample user"""
    
    print("🧪 Testing Webhook Processing...")
    
    # Try to find an existing user, or skip if none exists
    try:
        user = User.objects.first()
        if not user:
            print("⚠️  No users found in database. Skipping webhook test.")
            print("   Create a user account first to test webhook processing.")
            return None
        
        print(f"✅ Testing with user: {user.email}")
        
        # Sample email content
        raw_email = '''From: receipts@instacart.com
To: test@example.com
Subject: Your Instacart order has been delivered

Order #IC99999999
Delivered on January 18, 2024

2 x Organic Apples $4.99
1 x Almond Milk $3.49
1 x Whole Grain Bread $2.99

Subtotal: $11.47
Total: $12.59
'''
        
        # Process the email
        result = process_raw_email(raw_email, user.email)
        
        if result['success']:
            print(f"✅ Email processed successfully!")
            print(f"✅ Import Job ID: {result['import_job_id']}")
            print(f"✅ Items Found: {result.get('items_found', 0)}")
            print(f"✅ Confidence: {result.get('confidence_score', 0):.1%}")
        else:
            print(f"❌ Processing failed: {result['error']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Webhook test failed: {e}")
        return None

def test_store_detection():
    """Test store detection from different email senders"""
    
    print("🧪 Testing Store Detection...")
    
    parser = EnhancedReceiptParser()
    
    test_cases = [
        ('receipts@instacart.com', 'Your order', 'delivered', 'instacart'),
        ('auto-confirm@amazon.com', 'Amazon Fresh', 'delivered', 'amazon_fresh'), 
        ('no-reply@walmart.com', 'Walmart Grocery', 'pickup', 'walmart'),
        ('orders@target.com', 'Target order', 'ready', 'target'),
        ('receipts@kroger.com', 'Kroger delivery', 'complete', 'kroger'),
        ('unknown@store.com', 'Unknown store', 'receipt', None)
    ]
    
    for sender, subject, body, expected in test_cases:
        detected = parser._detect_store(sender, subject, body)
        status = "✅" if detected == expected else "❌"
        print(f"  {status} {sender} -> {detected or 'None'}")
    
    print()

def main():
    """Run all tests"""
    
    print("🚀 Starting Email Receipt Parsing Tests")
    print("=" * 50)
    
    # Test store detection
    test_store_detection()
    
    # Test receipt parsing
    instacart_result = test_instacart_receipt()
    print("-" * 50)
    
    amazon_result = test_amazon_fresh_receipt()
    print("-" * 50)
    
    walmart_result = test_walmart_receipt()
    print("-" * 50)
    
    # Test webhook processing (only if users exist)
    webhook_result = test_webhook_processing()
    print("-" * 50)
    
    # Summary
    print("📊 Test Summary:")
    print(f"✅ Instacart parsing: {len(instacart_result.items)} items, {instacart_result.confidence_score:.1%} confidence")
    print(f"✅ Amazon Fresh parsing: {len(amazon_result.items)} items, {amazon_result.confidence_score:.1%} confidence")
    print(f"✅ Walmart parsing: {len(walmart_result.items)} items, {walmart_result.confidence_score:.1%} confidence")
    
    if webhook_result:
        print(f"✅ Webhook processing: {webhook_result.get('items_found', 0)} items processed")
    else:
        print("⚠️  Webhook processing: Skipped (no users)")
    
    print("\n🎉 All tests completed!")
    print("\nNext steps:")
    print("1. Create a user account to test webhook processing")
    print("2. Test the web interface at /integrations/manual-upload/")
    print("3. Set up email forwarding to test real receipts")

if __name__ == '__main__':
    main()