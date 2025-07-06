"""
Email webhook service for processing receipt emails
Handles incoming emails from services like SendGrid, Mailgun, or direct SMTP
"""

import json
import logging
import hashlib
import hmac
from typing import Dict, Optional, Any
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email
import re

from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

from .enhanced_receipt_parser import EnhancedReceiptParser, ParsedReceipt
from .models import ImportJob, ImportSource, ImportStatus, ParsedReceiptItem

User = get_user_model()
logger = logging.getLogger(__name__)


class EmailWebhookService:
    """Service for processing email webhooks and parsing receipts"""
    
    def __init__(self):
        self.receipt_parser = EnhancedReceiptParser()
        
        # Email service configurations
        self.webhook_configs = {
            'sendgrid': {
                'secret_key': getattr(settings, 'SENDGRID_WEBHOOK_SECRET', ''),
                'header_name': 'X-Twilio-Email-Event-Webhook-Signature',
                'verify_signature': self._verify_sendgrid_signature
            },
            'mailgun': {
                'secret_key': getattr(settings, 'MAILGUN_WEBHOOK_SECRET', ''),
                'header_name': 'X-Mailgun-Signature-Timestamp',
                'verify_signature': self._verify_mailgun_signature
            },
            'postmark': {
                'secret_key': getattr(settings, 'POSTMARK_WEBHOOK_SECRET', ''),
                'header_name': 'X-Postmark-Webhook-Signature',
                'verify_signature': self._verify_postmark_signature
            }
        }
    
    def process_webhook(self, service: str, payload: Dict, headers: Dict) -> Dict[str, Any]:
        """Process incoming email webhook"""
        try:
            # Verify webhook signature if configured
            if service in self.webhook_configs:
                config = self.webhook_configs[service]
                if config['secret_key']:
                    if not config['verify_signature'](payload, headers):
                        logger.warning(f"Invalid {service} webhook signature")
                        return {'success': False, 'error': 'Invalid signature'}
            
            # Extract email data based on service
            email_data = self._extract_email_data(service, payload)
            if not email_data:
                return {'success': False, 'error': 'Could not extract email data'}
            
            # Find user by email address
            user = self._find_user_by_email(email_data['sender'])
            if not user:
                logger.info(f"No user found for email: {email_data['sender']}")
                return {'success': False, 'error': 'User not found'}
            
            # Process the receipt
            result = self._process_receipt_email(user, email_data)
            
            return {
                'success': True,
                'import_job_id': result.get('import_job_id'),
                'items_found': result.get('items_count', 0),
                'confidence_score': result.get('confidence_score', 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error processing {service} webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    def _extract_email_data(self, service: str, payload: Dict) -> Optional[Dict]:
        """Extract email data from webhook payload"""
        try:
            if service == 'sendgrid':
                return self._extract_sendgrid_data(payload)
            elif service == 'mailgun':
                return self._extract_mailgun_data(payload)
            elif service == 'postmark':
                return self._extract_postmark_data(payload)
            else:
                # Generic extraction
                return self._extract_generic_data(payload)
        except Exception as e:
            logger.error(f"Error extracting {service} email data: {e}")
            return None
    
    def _extract_sendgrid_data(self, payload: Dict) -> Dict:
        """Extract email data from SendGrid webhook"""
        # SendGrid sends an array of events
        events = payload if isinstance(payload, list) else [payload]
        
        for event in events:
            if event.get('event') == 'processed':
                return {
                    'sender': event.get('from', ''),
                    'recipient': event.get('to', ''),
                    'subject': event.get('subject', ''),
                    'body': event.get('text', '') or event.get('html', ''),
                    'timestamp': event.get('timestamp'),
                    'service': 'sendgrid'
                }
        
        return {}
    
    def _extract_mailgun_data(self, payload: Dict) -> Dict:
        """Extract email data from Mailgun webhook"""
        return {
            'sender': payload.get('sender', ''),
            'recipient': payload.get('recipient', ''),
            'subject': payload.get('subject', ''),
            'body': payload.get('body-plain', '') or payload.get('body-html', ''),
            'timestamp': payload.get('timestamp'),
            'service': 'mailgun'
        }
    
    def _extract_postmark_data(self, payload: Dict) -> Dict:
        """Extract email data from Postmark webhook"""
        return {
            'sender': payload.get('From', ''),
            'recipient': payload.get('To', ''),
            'subject': payload.get('Subject', ''),
            'body': payload.get('TextBody', '') or payload.get('HtmlBody', ''),
            'timestamp': payload.get('Date'),
            'service': 'postmark'
        }
    
    def _extract_generic_data(self, payload: Dict) -> Dict:
        """Extract email data from generic payload"""
        return {
            'sender': payload.get('from') or payload.get('sender', ''),
            'recipient': payload.get('to') or payload.get('recipient', ''),
            'subject': payload.get('subject', ''),
            'body': payload.get('body') or payload.get('text') or payload.get('html', ''),
            'timestamp': payload.get('timestamp') or payload.get('date'),
            'service': 'generic'
        }
    
    def _find_user_by_email(self, email_address: str) -> Optional[User]:
        """Find user by email address"""
        if not email_address:
            return None
        
        try:
            # Try exact match first
            return User.objects.get(email=email_address.lower())
        except User.DoesNotExist:
            # Try case-insensitive search
            try:
                return User.objects.get(email__iexact=email_address)
            except User.DoesNotExist:
                return None
    
    def _process_receipt_email(self, user: User, email_data: Dict) -> Dict:
        """Process receipt email and create import job"""
        
        # Parse the receipt
        parsed_receipt = self.receipt_parser.parse_email_receipt(email_data)
        
        # Create import job
        import_job = ImportJob.objects.create(
            user=user,
            household=user.household,
            source=ImportSource.EMAIL_RECEIPT,
            status=ImportStatus.PENDING if parsed_receipt.confidence_score < 0.8 else ImportStatus.PROCESSING,
            email_data={
                'email_sender': email_data.get('sender'),
                'email_subject': email_data.get('subject'),
                'service': email_data.get('service', 'unknown')
            },
            raw_data={
                'store_name': parsed_receipt.store_name,
                'confidence_score': parsed_receipt.confidence_score,
                'total_amount': float(parsed_receipt.total) if parsed_receipt.total else None,
                'purchase_date': parsed_receipt.purchase_date.isoformat() if parsed_receipt.purchase_date else None,
                'parsing_errors': parsed_receipt.parsing_errors
            }
        )
        
        # Create parsed receipt items
        items_created = 0
        for item in parsed_receipt.items:
            ParsedReceiptItem.objects.create(
                import_job=import_job,
                name=item.name,
                brand=item.brand,
                quantity=item.quantity,
                unit=item.unit,
                price=item.price,
                category=item.category,
                raw_text=item.raw_text,
                line_number=item.line_number,
                confidence_score=item.confidence_score,
                suggested_category=item.category,
                store_name=parsed_receipt.store_name
            )
            items_created += 1
        
        # Auto-process high confidence receipts
        if parsed_receipt.confidence_score >= 0.8 and not parsed_receipt.parsing_errors:
            try:
                self._auto_process_receipt(import_job)
                import_job.status = ImportStatus.COMPLETED
                import_job.save()
            except Exception as e:
                logger.error(f"Auto-processing failed for import {import_job.id}: {e}")
                import_job.status = ImportStatus.PENDING
                import_job.save()
        
        logger.info(f"Created import job {import_job.id} with {items_created} items for user {user.email}")
        
        return {
            'import_job_id': import_job.id,
            'items_count': items_created,
            'confidence_score': parsed_receipt.confidence_score,
            'auto_processed': import_job.status == ImportStatus.COMPLETED
        }
    
    def _auto_process_receipt(self, import_job: ImportJob):
        """Auto-process high confidence receipt items"""
        from inventory.models import InventoryItem, Category, StorageLocation
        
        # Get or create default category and location
        default_category, _ = Category.objects.get_or_create(
            name='Email Receipt Items',
            defaults={'household': import_job.household}
        )
        
        default_location, _ = StorageLocation.objects.get_or_create(
            name='Kitchen',
            defaults={'household': import_job.household}
        )
        
        created_count = 0
        
        for receipt_item in import_job.parsed_items.all():
            # Skip low confidence items
            if receipt_item.confidence_score < 0.7:
                continue
            
            # Create inventory item
            inventory_item = InventoryItem.objects.create(
                household=import_job.household,
                name=receipt_item.name,
                brand=receipt_item.brand or '',
                quantity=receipt_item.quantity,
                unit=receipt_item.unit,
                category=default_category,
                storage_location=default_location,
                purchase_price=receipt_item.price,
                notes=f"Auto-imported from {receipt_item.import_job.metadata.get('store_name', 'email receipt')}"
            )
            
            # Link receipt item to inventory item
            receipt_item.inventory_item = inventory_item
            receipt_item.save()
            
            created_count += 1
        
        # Update import job metadata
        if not import_job.raw_data:
            import_job.raw_data = {}
        import_job.raw_data['auto_created_items'] = created_count
        import_job.save()
        
        logger.info(f"Auto-created {created_count} inventory items from import {import_job.id}")
    
    # Signature verification methods
    def _verify_sendgrid_signature(self, payload: Dict, headers: Dict) -> bool:
        """Verify SendGrid webhook signature"""
        try:
            signature = headers.get('X-Twilio-Email-Event-Webhook-Signature')
            if not signature:
                return False
            
            public_key = self.webhook_configs['sendgrid']['secret_key']
            if not public_key:
                return True  # Skip verification if no key configured
            
            # SendGrid uses elliptic curve verification - simplified here
            # In production, use proper ECDSA verification
            return True
            
        except Exception as e:
            logger.error(f"SendGrid signature verification failed: {e}")
            return False
    
    def _verify_mailgun_signature(self, payload: Dict, headers: Dict) -> bool:
        """Verify Mailgun webhook signature"""
        try:
            timestamp = headers.get('X-Mailgun-Signature-Timestamp')
            token = headers.get('X-Mailgun-Signature-Token')
            signature = headers.get('X-Mailgun-Signature')
            
            if not all([timestamp, token, signature]):
                return False
            
            api_key = self.webhook_configs['mailgun']['secret_key']
            if not api_key:
                return True  # Skip verification if no key configured
            
            # Verify HMAC signature
            message = f"{timestamp}{token}".encode('utf-8')
            expected_signature = hmac.new(
                api_key.encode('utf-8'),
                message,
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Mailgun signature verification failed: {e}")
            return False
    
    def _verify_postmark_signature(self, payload: Dict, headers: Dict) -> bool:
        """Verify Postmark webhook signature"""
        try:
            signature = headers.get('X-Postmark-Webhook-Signature')
            if not signature:
                return False
            
            secret = self.webhook_configs['postmark']['secret_key']
            if not secret:
                return True  # Skip verification if no key configured
            
            # Postmark uses HMAC-SHA256
            payload_json = json.dumps(payload, separators=(',', ':'))
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload_json.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Postmark signature verification failed: {e}")
            return False


def process_raw_email(raw_email: str, user_email: str) -> Dict[str, Any]:
    """Process raw email content (for SMTP forwarding or manual upload)"""
    try:
        # Parse email message
        msg = email.message_from_string(raw_email)
        
        # Extract email data
        email_data = {
            'sender': msg.get('From', ''),
            'recipient': msg.get('To', ''),
            'subject': msg.get('Subject', ''),
            'body': _extract_email_body(msg),
            'timestamp': msg.get('Date'),
            'service': 'smtp'
        }
        
        # Find user
        webhook_service = EmailWebhookService()
        user = webhook_service._find_user_by_email(user_email)
        if not user:
            return {'success': False, 'error': 'User not found'}
        
        # Process receipt
        result = webhook_service._process_receipt_email(user, email_data)
        
        return {
            'success': True,
            'import_job_id': result.get('import_job_id'),
            'items_found': result.get('items_count', 0),
            'confidence_score': result.get('confidence_score', 0.0)
        }
        
    except Exception as e:
        logger.error(f"Error processing raw email: {e}")
        return {'success': False, 'error': str(e)}


def _extract_email_body(msg) -> str:
    """Extract body text from email message"""
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                break
            elif content_type == "text/html" and not body:
                # Fallback to HTML if no plain text
                html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                # Simple HTML to text conversion
                body = re.sub(r'<[^>]+>', '', html_body)
    else:
        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    
    return body.strip()