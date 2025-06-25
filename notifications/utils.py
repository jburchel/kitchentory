"""
Utility functions for sending notifications.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from typing import Dict, List, Optional
import logging

from .models import NotificationTemplate, InAppNotification, EmailDeliveryLog, DigestSchedule
from inventory.expiration_models import ExpirationAlert, UserNotificationPreferences
from analytics.utils import get_usage_analytics
from analytics.models import ReorderPrediction

logger = logging.getLogger(__name__)


def send_expiration_alerts(user, alerts: List[ExpirationAlert]) -> bool:
    """
    Send expiration alerts to a user via their preferred channels.
    
    Args:
        user: User to send alerts to
        alerts: List of ExpirationAlert instances
    
    Returns:
        True if at least one notification was sent successfully
    """
    preferences = UserNotificationPreferences.get_or_create_for_user(user)
    
    if not preferences.enable_expiration_alerts or not alerts:
        return False
    
    success = False
    
    # Group alerts by priority
    urgent_alerts = [a for a in alerts if a.priority == 'urgent']
    high_alerts = [a for a in alerts if a.priority == 'high']
    other_alerts = [a for a in alerts if a.priority in ['medium', 'low']]
    
    # Send email notifications
    if preferences.email_notifications:
        email_sent = _send_expiration_email(user, alerts, urgent_alerts, high_alerts)
        success = success or email_sent
    
    # Send in-app notifications
    if preferences.in_app_notifications:
        in_app_sent = _send_expiration_in_app_notifications(user, urgent_alerts + high_alerts)
        success = success or in_app_sent
    
    # Send push notifications for urgent items
    if preferences.push_notifications and urgent_alerts:
        push_sent = _send_expiration_push_notifications(user, urgent_alerts)
        success = success or push_sent
    
    return success


def _send_expiration_email(user, all_alerts: List[ExpirationAlert], 
                          urgent_alerts: List[ExpirationAlert], 
                          high_alerts: List[ExpirationAlert]) -> bool:
    """Send expiration alert email."""
    try:
        template = NotificationTemplate.objects.get(
            template_type='expiration_alert',
            is_active=True
        )
    except NotificationTemplate.DoesNotExist:
        logger.error("Expiration alert email template not found")
        return False
    
    # Prepare context data
    context_data = {
        'user': user,
        'urgent_alerts': urgent_alerts,
        'high_alerts': high_alerts,
        'total_alerts': len(all_alerts),
        'urgent_count': len(urgent_alerts),
        'high_count': len(high_alerts),
        'dashboard_url': f"{settings.SITE_URL}/inventory/expiration/",
    }
    
    # Render templates
    context = Context(context_data)
    subject = Template(template.subject_template).render(context)
    html_content = Template(template.html_template).render(context)
    text_content = Template(template.text_template).render(context) if template.text_template else None
    
    # Create email delivery log
    delivery_log = EmailDeliveryLog.objects.create(
        user=user,
        template_type='expiration_alert',
        subject=subject,
        recipient_email=user.email,
        status='pending'
    )
    
    try:
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content or html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        
        if html_content:
            email.attach_alternative(html_content, "text/html")
        
        email.send()
        
        # Update delivery log
        delivery_log.status = 'sent'
        delivery_log.sent_at = timezone.now()
        delivery_log.save()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send expiration alert email to {user.email}: {str(e)}")
        delivery_log.status = 'failed'
        delivery_log.error_message = str(e)
        delivery_log.save()
        return False


def _send_expiration_in_app_notifications(user, alerts: List[ExpirationAlert]) -> bool:
    """Send in-app notifications for expiration alerts."""
    success = False
    
    for alert in alerts:
        try:
            # Determine notification type and priority
            notification_type = 'expiration'
            priority = 'urgent' if alert.priority == 'urgent' else 'high'
            
            # Create in-app notification
            notification = InAppNotification.objects.create(
                user=user,
                title=f"Food Expiration Alert",
                message=alert.message,
                notification_type=notification_type,
                priority=priority,
                action_url=f"/inventory/expiration/",
                action_text="View Details",
                related_object_type='expiration_alert',
                related_object_id=str(alert.id),
                expires_at=timezone.now() + timezone.timedelta(days=7)
            )
            
            success = True
            
        except Exception as e:
            logger.error(f"Failed to create in-app notification for alert {alert.id}: {str(e)}")
    
    return success


def _send_expiration_push_notifications(user, alerts: List[ExpirationAlert]) -> bool:
    """Send push notifications for urgent expiration alerts."""
    # Push notifications would require a service like Firebase Cloud Messaging
    # For now, this is a placeholder implementation
    
    try:
        template = NotificationTemplate.objects.get(
            template_type='expiration_alert',
            is_active=True
        )
    except NotificationTemplate.DoesNotExist:
        return False
    
    if not template.push_title_template or not template.push_body_template:
        return False
    
    for alert in alerts:
        context_data = {
            'alert': alert,
            'user': user,
            'product_name': alert.inventory_item.product.name,
            'days_until_expiration': alert.days_until_expiration,
        }
        
        context = Context(context_data)
        title = Template(template.push_title_template).render(context)
        body = Template(template.push_body_template).render(context)
        
        # TODO: Implement actual push notification sending
        # This would typically involve:
        # 1. Getting user's device tokens
        # 2. Sending to push notification service (FCM, APNs, etc.)
        # 3. Handling delivery confirmations
        
        logger.info(f"Push notification would be sent: {title} - {body}")
    
    return True


def send_daily_digest(user) -> bool:
    """
    Send daily digest email to user.
    
    Args:
        user: User to send digest to
    
    Returns:
        True if digest was sent successfully
    """
    preferences = UserNotificationPreferences.get_or_create_for_user(user)
    
    if not preferences.daily_digest or not preferences.email_notifications:
        return False
    
    try:
        template = NotificationTemplate.objects.get(
            template_type='daily_digest',
            is_active=True
        )
    except NotificationTemplate.DoesNotExist:
        logger.error("Daily digest email template not found")
        return False
    
    # Get digest data
    digest_data = _prepare_digest_data(user, 'daily')
    
    if not _should_send_digest(digest_data):
        return False
    
    # Render templates
    context = Context(digest_data)
    subject = Template(template.subject_template).render(context)
    html_content = Template(template.html_template).render(context)
    text_content = Template(template.text_template).render(context) if template.text_template else None
    
    return _send_digest_email(user, 'daily_digest', subject, html_content, text_content)


def send_weekly_digest(user) -> bool:
    """Send weekly digest email to user."""
    preferences = UserNotificationPreferences.get_or_create_for_user(user)
    
    if not preferences.weekly_digest or not preferences.email_notifications:
        return False
    
    try:
        template = NotificationTemplate.objects.get(
            template_type='weekly_digest',
            is_active=True
        )
    except NotificationTemplate.DoesNotExist:
        logger.error("Weekly digest email template not found")
        return False
    
    # Get digest data
    digest_data = _prepare_digest_data(user, 'weekly')
    
    # Render templates
    context = Context(digest_data)
    subject = Template(template.subject_template).render(context)
    html_content = Template(template.html_template).render(context)
    text_content = Template(template.text_template).render(context) if template.text_template else None
    
    return _send_digest_email(user, 'weekly_digest', subject, html_content, text_content)


def _prepare_digest_data(user, digest_type: str) -> Dict:
    """Prepare data for digest emails."""
    from inventory.expiration_utils import get_expiration_dashboard_data
    from shopping.models import ShoppingList
    
    days = 1 if digest_type == 'daily' else 7
    
    # Get expiration data
    expiration_data = get_expiration_dashboard_data(user)
    
    # Get usage analytics
    usage_data = get_usage_analytics(user, days=days)
    
    # Get active shopping lists
    active_shopping_lists = ShoppingList.objects.filter(
        created_by=user,
        status__in=['active', 'shopping']
    ).count()
    
    # Get reorder predictions
    due_predictions = ReorderPrediction.objects.filter(
        user=user,
        status='pending',
        predicted_reorder_date__lte=timezone.now().date() + timezone.timedelta(days=7)
    ).count()
    
    return {
        'user': user,
        'digest_type': digest_type,
        'period_days': days,
        'expiration_data': expiration_data,
        'usage_data': usage_data,
        'active_shopping_lists': active_shopping_lists,
        'due_predictions': due_predictions,
        'dashboard_url': f"{settings.SITE_URL}/dashboard/",
        'expiration_url': f"{settings.SITE_URL}/inventory/expiration/",
        'shopping_url': f"{settings.SITE_URL}/shopping/",
        'unsubscribe_url': f"{settings.SITE_URL}/notifications/unsubscribe/",
    }


def _should_send_digest(digest_data: Dict) -> bool:
    """Determine if digest should be sent based on content."""
    expiration_data = digest_data.get('expiration_data', {})
    usage_data = digest_data.get('usage_data', {})
    
    # Send if there are urgent alerts or significant activity
    urgent_alerts = expiration_data.get('alerts', {}).get('urgent_count', 0)
    usage_events = usage_data.get('total_usage_events', 0)
    
    return urgent_alerts > 0 or usage_events > 0 or digest_data.get('due_predictions', 0) > 0


def _send_digest_email(user, template_type: str, subject: str, 
                      html_content: str, text_content: str = None) -> bool:
    """Send digest email and log delivery."""
    delivery_log = EmailDeliveryLog.objects.create(
        user=user,
        template_type=template_type,
        subject=subject,
        recipient_email=user.email,
        status='pending'
    )
    
    try:
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content or html_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        
        if html_content:
            email.attach_alternative(html_content, "text/html")
        
        email.send()
        
        delivery_log.status = 'sent'
        delivery_log.sent_at = timezone.now()
        delivery_log.save()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send {template_type} email to {user.email}: {str(e)}")
        delivery_log.status = 'failed'
        delivery_log.error_message = str(e)
        delivery_log.save()
        return False


def create_notification(user, title: str, message: str, 
                       notification_type: str = 'info', priority: str = 'normal',
                       action_url: str = None, action_text: str = None,
                       expires_days: int = 7) -> InAppNotification:
    """
    Create an in-app notification for a user.
    
    Args:
        user: User to notify
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        priority: Priority level
        action_url: Optional action URL
        action_text: Optional action button text
        expires_days: Days until notification expires
    
    Returns:
        Created InAppNotification instance
    """
    expires_at = timezone.now() + timezone.timedelta(days=expires_days)
    
    notification = InAppNotification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action_url=action_url,
        action_text=action_text,
        expires_at=expires_at
    )
    
    return notification


def get_user_notifications(user, limit: int = 20, unread_only: bool = False) -> List[InAppNotification]:
    """
    Get user's in-app notifications.
    
    Args:
        user: User to get notifications for
        limit: Maximum number of notifications to return
        unread_only: Only return unread notifications
    
    Returns:
        List of InAppNotification instances
    """
    notifications = InAppNotification.objects.filter(
        user=user,
        is_dismissed=False
    )
    
    if unread_only:
        notifications = notifications.filter(is_read=False)
    
    # Filter out expired notifications
    notifications = notifications.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )
    
    return list(notifications.order_by('-created_at')[:limit])


def mark_notifications_read(user, notification_ids: List[int] = None) -> int:
    """
    Mark notifications as read.
    
    Args:
        user: User whose notifications to mark
        notification_ids: Specific notification IDs to mark (None for all)
    
    Returns:
        Number of notifications marked as read
    """
    notifications = InAppNotification.objects.filter(
        user=user,
        is_read=False,
        is_dismissed=False
    )
    
    if notification_ids:
        notifications = notifications.filter(id__in=notification_ids)
    
    count = 0
    for notification in notifications:
        notification.mark_read()
        count += 1
    
    return count


def cleanup_old_notifications(days: int = 30) -> int:
    """
    Clean up old notifications.
    
    Args:
        days: Age in days for notifications to be considered old
    
    Returns:
        Number of notifications deleted
    """
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    
    # Delete old dismissed notifications
    old_notifications = InAppNotification.objects.filter(
        Q(is_dismissed=True, dismissed_at__lt=cutoff_date) |
        Q(expires_at__lt=cutoff_date)
    )
    
    count = old_notifications.count()
    old_notifications.delete()
    
    return count