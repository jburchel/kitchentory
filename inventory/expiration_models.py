"""
Extended models for expiration tracking and waste management.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

User = get_user_model()


class ExpirationAlert(models.Model):
    """
    Expiration alerts for inventory items.
    """

    ALERT_TYPES = (
        ("expiring_soon", _("Expiring Soon")),
        ("expired", _("Expired")),
        ("use_first", _("Use First")),
        ("opened_item", _("Opened Item")),
    )

    ALERT_PRIORITIES = (
        ("low", _("Low")),
        ("medium", _("Medium")),
        ("high", _("High")),
        ("urgent", _("Urgent")),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="expiration_alerts"
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.CASCADE,
        related_name="expiration_alerts",
    )

    alert_type = models.CharField(_("alert type"), max_length=20, choices=ALERT_TYPES)
    priority = models.CharField(
        _("priority"), max_length=10, choices=ALERT_PRIORITIES, default="medium"
    )

    # Alert timing
    alert_date = models.DateField(_("alert date"))
    days_until_expiration = models.IntegerField(_("days until expiration"))

    # Status
    is_acknowledged = models.BooleanField(_("acknowledged"), default=False)
    acknowledged_at = models.DateTimeField(_("acknowledged at"), null=True, blank=True)
    is_dismissed = models.BooleanField(_("dismissed"), default=False)
    dismissed_at = models.DateTimeField(_("dismissed at"), null=True, blank=True)

    # Auto-generated fields
    message = models.TextField(_("alert message"))
    suggested_action = models.CharField(
        _("suggested action"), max_length=200, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expiration_alerts"
        verbose_name = _("expiration alert")
        verbose_name_plural = _("expiration alerts")
        ordering = ["-priority", "alert_date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "is_acknowledged", "is_dismissed"]),
            models.Index(fields=["alert_date", "priority"]),
        ]

    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.inventory_item.product.name}"

    def acknowledge(self):
        """Mark alert as acknowledged."""
        self.is_acknowledged = True
        self.acknowledged_at = timezone.now()
        self.save(update_fields=["is_acknowledged", "acknowledged_at"])

    def dismiss(self):
        """Dismiss the alert."""
        self.is_dismissed = True
        self.dismissed_at = timezone.now()
        self.save(update_fields=["is_dismissed", "dismissed_at"])

    @property
    def is_active(self):
        """Check if alert is still active."""
        return not self.is_dismissed and not self.is_acknowledged


class WasteLog(models.Model):
    """
    Track food waste to provide insights and reduce waste.
    """

    WASTE_REASONS = (
        ("expired", _("Expired")),
        ("spoiled", _("Spoiled")),
        ("moldy", _("Moldy")),
        ("freezer_burn", _("Freezer Burn")),
        ("taste_bad", _("Tasted Bad")),
        ("forgotten", _("Forgotten")),
        ("too_much", _("Bought Too Much")),
        ("quality_decline", _("Quality Decline")),
        ("accident", _("Accident")),
        ("other", _("Other")),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="waste_logs")
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.CASCADE,
        related_name="waste_logs",
        null=True,
        blank=True,
    )

    # Product info (in case inventory item is deleted)
    product_name = models.CharField(_("product name"), max_length=200)
    category_name = models.CharField(_("category"), max_length=100, blank=True)

    # Waste details
    waste_reason = models.CharField(
        _("waste reason"), max_length=20, choices=WASTE_REASONS
    )
    quantity_wasted = models.DecimalField(
        _("quantity wasted"), max_digits=10, decimal_places=2
    )
    unit = models.CharField(_("unit"), max_length=10)

    # Financial impact
    estimated_value = models.DecimalField(
        _("estimated value"), max_digits=10, decimal_places=2, null=True, blank=True
    )

    # Timing
    waste_date = models.DateField(_("waste date"), default=timezone.now)
    purchase_date = models.DateField(_("original purchase date"), null=True, blank=True)
    expiration_date = models.DateField(_("expiration date"), null=True, blank=True)

    # Prevention insights
    could_have_been_prevented = models.BooleanField(
        _("could have been prevented"), default=True
    )
    prevention_notes = models.TextField(_("prevention notes"), blank=True)

    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "waste_logs"
        verbose_name = _("waste log")
        verbose_name_plural = _("waste logs")
        ordering = ["-waste_date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "waste_date"]),
            models.Index(fields=["waste_reason"]),
        ]

    def __str__(self):
        return f"Wasted {self.quantity_wasted} {self.unit} of {self.product_name}"

    @property
    def days_from_purchase_to_waste(self):
        """Calculate days from purchase to waste."""
        if self.purchase_date:
            return (self.waste_date - self.purchase_date).days
        return None

    @property
    def days_past_expiration(self):
        """Calculate days past expiration when wasted."""
        if self.expiration_date:
            return (self.waste_date - self.expiration_date).days
        return None


class UserNotificationPreferences(models.Model):
    """
    User preferences for expiration and waste notifications.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="notification_preferences"
    )

    # Expiration alert preferences
    enable_expiration_alerts = models.BooleanField(
        _("enable expiration alerts"), default=True
    )
    alert_days_before_expiration = models.IntegerField(
        _("alert days before expiration"),
        default=3,
        help_text=_("How many days before expiration to send alerts"),
    )
    urgent_alert_days = models.IntegerField(
        _("urgent alert days"),
        default=1,
        help_text=_("Days before expiration for urgent alerts"),
    )

    # Notification channels
    email_notifications = models.BooleanField(_("email notifications"), default=True)
    push_notifications = models.BooleanField(_("push notifications"), default=True)
    in_app_notifications = models.BooleanField(_("in-app notifications"), default=True)

    # Digest preferences
    daily_digest = models.BooleanField(_("daily digest"), default=False)
    weekly_digest = models.BooleanField(_("weekly digest"), default=True)
    digest_email_time = models.TimeField(
        _("digest email time"),
        default="08:00",
        help_text=_("Time to send digest emails"),
    )

    # Specific alert types
    alert_expiring_soon = models.BooleanField(
        _("alert for expiring soon"), default=True
    )
    alert_expired = models.BooleanField(_("alert for expired items"), default=True)
    alert_opened_items = models.BooleanField(_("alert for opened items"), default=True)
    alert_use_first = models.BooleanField(_("alert for use first items"), default=True)

    # Waste tracking
    enable_waste_tracking = models.BooleanField(
        _("enable waste tracking"), default=True
    )
    waste_report_frequency = models.CharField(
        _("waste report frequency"),
        max_length=10,
        choices=(
            ("never", _("Never")),
            ("weekly", _("Weekly")),
            ("monthly", _("Monthly")),
            ("quarterly", _("Quarterly")),
        ),
        default="monthly",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_notification_preferences"
        verbose_name = _("notification preferences")
        verbose_name_plural = _("notification preferences")

    def __str__(self):
        return f"Notification preferences for {self.user.username}"

    @classmethod
    def get_or_create_for_user(cls, user):
        """Get or create notification preferences for a user."""
        preferences, created = cls.objects.get_or_create(
            user=user,
            defaults={
                "enable_expiration_alerts": True,
                "alert_days_before_expiration": 3,
                "urgent_alert_days": 1,
                "email_notifications": True,
                "weekly_digest": True,
            },
        )
        return preferences


class ExpirationRule(models.Model):
    """
    Custom expiration rules for specific products or categories.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="expiration_rules"
    )

    # Rule targeting
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="expiration_rules",
    )
    category = models.ForeignKey(
        "inventory.Category",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="expiration_rules",
    )

    # Rule details
    name = models.CharField(_("rule name"), max_length=100)
    description = models.TextField(_("description"), blank=True)

    # Timing adjustments
    shelf_life_days = models.IntegerField(
        _("shelf life days"),
        null=True,
        blank=True,
        help_text=_("Override default shelf life"),
    )
    opened_shelf_life_days = models.IntegerField(
        _("opened shelf life days"),
        null=True,
        blank=True,
        help_text=_("Shelf life after opening"),
    )
    alert_days_before = models.IntegerField(
        _("alert days before expiration"),
        null=True,
        blank=True,
        help_text=_("Custom alert timing for this rule"),
    )

    # Storage conditions
    requires_refrigeration = models.BooleanField(
        _("requires refrigeration"), default=False
    )
    requires_freezing = models.BooleanField(_("requires freezing"), default=False)

    is_active = models.BooleanField(_("active"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expiration_rules"
        verbose_name = _("expiration rule")
        verbose_name_plural = _("expiration rules")
        ordering = ["name"]

    def __str__(self):
        target = (
            self.product.name
            if self.product
            else self.category.name if self.category else "General"
        )
        return f"{self.name} ({target})"

    def applies_to_item(self, inventory_item):
        """Check if this rule applies to an inventory item."""
        if self.product and inventory_item.product == self.product:
            return True
        if self.category and inventory_item.product.category == self.category:
            return True
        return False
