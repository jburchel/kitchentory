from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import Household

User = get_user_model()


class ImportSource(models.TextChoices):
    EMAIL_RECEIPT = "email", "Email Receipt"
    CSV_UPLOAD = "csv", "CSV Upload"
    BROWSER_EXTENSION = "browser", "Browser Extension"
    STORE_API = "api", "Store API"


class ImportStatus(models.TextChoices):
    PENDING = "pending", "Pending Review"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ImportJob(models.Model):
    """Track import jobs from various sources"""

    id = models.AutoField(primary_key=True)
    household = models.ForeignKey(Household, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    source = models.CharField(max_length=20, choices=ImportSource.choices)
    status = models.CharField(
        max_length=20, choices=ImportStatus.choices, default=ImportStatus.PENDING
    )

    # Source-specific data
    email_data = models.JSONField(null=True, blank=True)  # Email details
    file_path = models.CharField(max_length=500, blank=True)  # For CSV uploads
    store_data = models.JSONField(null=True, blank=True)  # Store API data

    # Processing results
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    created_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)

    # Parsed data
    raw_data = models.JSONField(null=True, blank=True)  # Original parsed data
    validated_data = models.JSONField(null=True, blank=True)  # Cleaned/validated data
    errors = models.JSONField(null=True, blank=True)  # Processing errors

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Import {self.id} - {self.get_source_display()} ({self.status})"


class EmailReceiptConfig(models.Model):
    """Configuration for email receipt parsing"""

    household = models.OneToOneField(Household, on_delete=models.CASCADE)

    # Email settings
    email_address = models.EmailField(
        help_text="Dedicated email for receipt forwarding"
    )
    webhook_secret = models.CharField(max_length=100, blank=True)

    # Parsing preferences
    auto_approve = models.BooleanField(
        default=False, help_text="Automatically add items without review"
    )
    confidence_threshold = models.FloatField(
        default=0.8, help_text="Minimum confidence for auto-approval"
    )

    # Store mappings
    store_mappings = models.JSONField(
        default=dict, help_text="Map email senders to store names"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Email config for {self.household.name}"


class ParsedReceiptItem(models.Model):
    """Individual items parsed from receipts"""

    import_job = models.ForeignKey(
        ImportJob, on_delete=models.CASCADE, related_name="parsed_items"
    )

    # Original parsed data
    raw_text = models.TextField(blank=True)
    line_number = models.IntegerField(null=True, blank=True)

    # Parsed item data
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=100, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    unit = models.CharField(max_length=20, default="item")
    price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Matching confidence
    confidence_score = models.FloatField(null=True, blank=True)
    suggested_product_id = models.IntegerField(null=True, blank=True)
    suggested_category = models.CharField(max_length=100, blank=True)

    # Processing status
    is_processed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_inventory_item_id = models.IntegerField(null=True, blank=True)

    # Metadata
    store_name = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["line_number", "name"]

    def __str__(self):
        return f"{self.name} (x{self.quantity})"


class StoreAPICredential(models.Model):
    """Store API credentials for direct integration"""

    household = models.ForeignKey(Household, on_delete=models.CASCADE)
    store_name = models.CharField(max_length=100)

    # API credentials (encrypted)
    api_key = models.TextField(blank=True)
    api_secret = models.TextField(blank=True)
    access_token = models.TextField(blank=True)
    refresh_token = models.TextField(blank=True)

    # Settings
    auto_sync = models.BooleanField(default=False)
    sync_frequency = models.CharField(max_length=20, default="daily")
    last_sync = models.DateTimeField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["household", "store_name"]

    def __str__(self):
        return f"{self.store_name} API for {self.household.name}"
