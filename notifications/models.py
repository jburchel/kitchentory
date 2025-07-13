"""
Models for notification system.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

User = get_user_model()


class NotificationTemplate(models.Model):
    """
    Email and notification templates.
    """

    TEMPLATE_TYPES = (
        ("expiration_alert", _("Expiration Alert")),
        ("daily_digest", _("Daily Digest")),
        ("weekly_digest", _("Weekly Digest")),
        ("shopping_reminder", _("Shopping Reminder")),
        ("recipe_suggestion", _("Recipe Suggestion")),
        ("waste_report", _("Waste Report")),
        ("budget_alert", _("Budget Alert")),
        ("welcome", _("Welcome")),
    )

    name = models.CharField(_("template name"), max_length=100)
    template_type = models.CharField(
        _("template type"), max_length=20, choices=TEMPLATE_TYPES
    )

    # Email template content
    subject_template = models.CharField(_("subject template"), max_length=200)
    html_template = models.TextField(_("HTML template"))
    text_template = models.TextField(_("text template"), blank=True)

    # Push notification content
    push_title_template = models.CharField(
        _("push title template"), max_length=100, blank=True
    )
    push_body_template = models.CharField(
        _("push body template"), max_length=200, blank=True
    )

    # In-app notification content
    in_app_title_template = models.CharField(
        _("in-app title template"), max_length=100, blank=True
    )
    in_app_message_template = models.TextField(_("in-app message template"), blank=True)

    is_active = models.BooleanField(_("active"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_templates"
        verbose_name = _("notification template")
        verbose_name_plural = _("notification templates")
        unique_together = ["template_type"]

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class InAppNotification(models.Model):
    """
    In-app notifications for users.
    """

    NOTIFICATION_TYPES = (
        ("info", _("Information")),
        ("warning", _("Warning")),
        ("success", _("Success")),
        ("error", _("Error")),
        ("expiration", _("Expiration Alert")),
        ("shopping", _("Shopping Reminder")),
        ("recipe", _("Recipe Suggestion")),
        ("budget", _("Budget Alert")),
    )

    PRIORITY_LEVELS = (
        ("low", _("Low")),
        ("normal", _("Normal")),
        ("high", _("High")),
        ("urgent", _("Urgent")),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="in_app_notifications"
    )

    # Content
    title = models.CharField(_("title"), max_length=100)
    message = models.TextField(_("message"))
    notification_type = models.CharField(
        _("notification type"),
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default="info",
    )
    priority = models.CharField(
        _("priority"), max_length=10, choices=PRIORITY_LEVELS, default="normal"
    )

    # Actions
    action_url = models.URLField(_("action URL"), blank=True)
    action_text = models.CharField(_("action text"), max_length=50, blank=True)

    # Status
    is_read = models.BooleanField(_("read"), default=False)
    read_at = models.DateTimeField(_("read at"), null=True, blank=True)
    is_dismissed = models.BooleanField(_("dismissed"), default=False)
    dismissed_at = models.DateTimeField(_("dismissed at"), null=True, blank=True)

    # Metadata
    related_object_type = models.CharField(
        _("related object type"), max_length=50, blank=True
    )
    related_object_id = models.CharField(
        _("related object ID"), max_length=100, blank=True
    )

    expires_at = models.DateTimeField(_("expires at"), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "in_app_notifications"
        verbose_name = _("in-app notification")
        verbose_name_plural = _("in-app notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read", "is_dismissed"]),
            models.Index(fields=["created_at", "priority"]),
        ]

    def __str__(self):
        return f"{self.title} for {self.user.username}"

    def mark_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    def dismiss(self):
        """Dismiss the notification."""
        if not self.is_dismissed:
            self.is_dismissed = True
            self.dismissed_at = timezone.now()
            self.save(update_fields=["is_dismissed", "dismissed_at"])

    @property
    def is_active(self):
        """Check if notification is still active."""
        if self.is_dismissed:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class EmailDeliveryLog(models.Model):
    """
    Log of email deliveries for tracking and debugging.
    """

    STATUS_CHOICES = (
        ("pending", _("Pending")),
        ("sent", _("Sent")),
        ("delivered", _("Delivered")),
        ("failed", _("Failed")),
        ("bounced", _("Bounced")),
        ("complained", _("Complained")),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="email_deliveries"
    )

    # Email details
    template_type = models.CharField(_("template type"), max_length=20)
    subject = models.CharField(_("subject"), max_length=200)
    recipient_email = models.EmailField(_("recipient email"))

    # Status tracking
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    # Timestamps
    sent_at = models.DateTimeField(_("sent at"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("delivered at"), null=True, blank=True)
    opened_at = models.DateTimeField(_("opened at"), null=True, blank=True)
    clicked_at = models.DateTimeField(_("clicked at"), null=True, blank=True)

    # Error tracking
    error_message = models.TextField(_("error message"), blank=True)
    retry_count = models.IntegerField(_("retry count"), default=0)

    # External IDs (for email service provider)
    external_message_id = models.CharField(
        _("external message ID"), max_length=100, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "email_delivery_log"
        verbose_name = _("email delivery log")
        verbose_name_plural = _("email delivery logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["template_type", "sent_at"]),
        ]

    def __str__(self):
        return f"{self.template_type} email to {self.recipient_email} ({self.status})"


class DigestSchedule(models.Model):
    """
    Schedule for digest emails.
    """

    DIGEST_TYPES = (
        ("daily", _("Daily Digest")),
        ("weekly", _("Weekly Digest")),
        ("monthly", _("Monthly Digest")),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="digest_schedules"
    )

    digest_type = models.CharField(
        _("digest type"), max_length=10, choices=DIGEST_TYPES
    )

    # Schedule settings
    is_enabled = models.BooleanField(_("enabled"), default=True)
    send_time = models.TimeField(_("send time"), default="08:00")

    # For weekly digests
    weekday = models.IntegerField(
        _("weekday"), null=True, blank=True, help_text=_("0=Monday, 6=Sunday")
    )

    # For monthly digests
    day_of_month = models.IntegerField(
        _("day of month"),
        null=True,
        blank=True,
        help_text=_("1-28, day of month to send"),
    )

    # Tracking
    last_sent = models.DateTimeField(_("last sent"), null=True, blank=True)
    next_send = models.DateTimeField(_("next send"), null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "digest_schedules"
        verbose_name = _("digest schedule")
        verbose_name_plural = _("digest schedules")
        unique_together = ["user", "digest_type"]

    def __str__(self):
        return f"{self.user.username} {self.get_digest_type_display()}"

    def calculate_next_send(self):
        """Calculate the next send time for this digest."""
        from datetime import datetime, timedelta
        import calendar

        now = timezone.now()
        today = now.date()
        send_datetime = timezone.make_aware(datetime.combine(today, self.send_time))

        if self.digest_type == "daily":
            # Send every day at the specified time
            if send_datetime <= now:
                send_datetime += timedelta(days=1)
            self.next_send = send_datetime

        elif self.digest_type == "weekly":
            # Send on specified weekday
            current_weekday = today.weekday()
            target_weekday = (
                self.weekday if self.weekday is not None else 0
            )  # Default to Monday

            days_ahead = target_weekday - current_weekday
            if days_ahead <= 0:  # Target day already passed this week
                days_ahead += 7

            target_date = today + timedelta(days=days_ahead)
            send_datetime = timezone.make_aware(
                datetime.combine(target_date, self.send_time)
            )

            # If it's the target day but past send time, schedule for next week
            if target_date == today and send_datetime <= now:
                send_datetime += timedelta(days=7)

            self.next_send = send_datetime

        elif self.digest_type == "monthly":
            # Send on specified day of month
            target_day = self.day_of_month if self.day_of_month is not None else 1

            # Calculate next occurrence
            year, month = today.year, today.month

            # Get the last day of current month
            last_day = calendar.monthrange(year, month)[1]
            target_day = min(target_day, last_day)

            if today.day >= target_day:
                # Move to next month
                if month == 12:
                    year += 1
                    month = 1
                else:
                    month += 1

                # Adjust target day for new month
                last_day = calendar.monthrange(year, month)[1]
                target_day = min(self.day_of_month or 1, last_day)

            target_date = today.replace(year=year, month=month, day=target_day)
            send_datetime = timezone.make_aware(
                datetime.combine(target_date, self.send_time)
            )

            self.next_send = send_datetime

        self.save(update_fields=["next_send"])
