"""
Serializers for integrations app
"""

from rest_framework import serializers
from .models import ImportJob, ParsedReceiptItem, EmailReceiptConfig
from .csv_import import ImportPreview, ValidationError, ImportMapping


class ImportMappingSerializer(serializers.Serializer):
    """Serializer for CSV column mapping"""

    name = serializers.CharField(required=False, allow_blank=True)
    brand = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.CharField(required=False, allow_blank=True)
    unit = serializers.CharField(required=False, allow_blank=True)
    price = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    expiration_date = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    barcode = serializers.CharField(required=False, allow_blank=True)


class ValidationErrorSerializer(serializers.Serializer):
    """Serializer for validation errors"""

    row = serializers.IntegerField()
    field = serializers.CharField()
    value = serializers.CharField()
    message = serializers.CharField()


class ImportPreviewSerializer(serializers.Serializer):
    """Serializer for import preview data"""

    total_rows = serializers.IntegerField()
    valid_rows = serializers.IntegerField()
    invalid_rows = serializers.IntegerField()
    sample_data = serializers.ListField(child=serializers.DictField())
    errors = ValidationErrorSerializer(many=True)
    suggested_mappings = ImportMappingSerializer()
    column_names = serializers.ListField(child=serializers.CharField())


class ParsedReceiptItemSerializer(serializers.ModelSerializer):
    """Serializer for parsed receipt items"""

    class Meta:
        model = ParsedReceiptItem
        fields = [
            "id",
            "name",
            "brand",
            "quantity",
            "unit",
            "price",
            "confidence_score",
            "suggested_category",
            "is_processed",
            "is_approved",
            "store_name",
            "purchase_date",
            "raw_text",
            "line_number",
            "created_at",
        ]


class ImportJobSerializer(serializers.ModelSerializer):
    """Serializer for import jobs"""

    source_display = serializers.CharField(source="get_source_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    parsed_items = ParsedReceiptItemSerializer(many=True, read_only=True)

    # Computed fields
    success_rate = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "source",
            "source_display",
            "status",
            "status_display",
            "total_items",
            "processed_items",
            "created_items",
            "failed_items",
            "success_rate",
            "duration",
            "file_path",
            "errors",
            "created_at",
            "updated_at",
            "completed_at",
            "parsed_items",
        ]

    def get_success_rate(self, obj):
        """Calculate success rate as percentage"""
        if obj.total_items == 0:
            return 0
        return round((obj.created_items / obj.total_items) * 100, 1)

    def get_duration(self, obj):
        """Calculate processing duration in seconds"""
        if not obj.completed_at:
            return None

        start_time = obj.created_at
        end_time = obj.completed_at

        duration = (end_time - start_time).total_seconds()
        return round(duration, 1)


class ImportJobSummarySerializer(serializers.ModelSerializer):
    """Simplified serializer for import job lists"""

    source_display = serializers.CharField(source="get_source_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    success_rate = serializers.SerializerMethodField()

    class Meta:
        model = ImportJob
        fields = [
            "id",
            "source",
            "source_display",
            "status",
            "status_display",
            "total_items",
            "created_items",
            "failed_items",
            "success_rate",
            "file_path",
            "created_at",
            "completed_at",
        ]

    def get_success_rate(self, obj):
        """Calculate success rate as percentage"""
        if obj.total_items == 0:
            return 0
        return round((obj.created_items / obj.total_items) * 100, 1)


class EmailReceiptConfigSerializer(serializers.ModelSerializer):
    """Serializer for email receipt configuration"""

    class Meta:
        model = EmailReceiptConfig
        fields = [
            "id",
            "email_address",
            "auto_approve",
            "confidence_threshold",
            "store_mappings",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["webhook_secret"]


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload validation"""

    file = serializers.FileField()
    mapping = ImportMappingSerializer(required=False)

    def validate_file(self, value):
        """Validate uploaded file"""
        # File size limit (10MB)
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File too large. Maximum size is {max_size // (1024*1024)}MB"
            )

        # File type validation
        allowed_extensions = [".csv", ".xlsx", ".xls"]
        file_extension = (
            "." + value.name.split(".")[-1].lower() if "." in value.name else ""
        )

        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed types: {', '.join(allowed_extensions)}"
            )

        return value


class BulkImportStatsSerializer(serializers.Serializer):
    """Serializer for bulk import statistics"""

    total_jobs = serializers.IntegerField()
    completed_jobs = serializers.IntegerField()
    failed_jobs = serializers.IntegerField()
    total_items_imported = serializers.IntegerField()
    success_rate = serializers.FloatField()
    average_items_per_job = serializers.FloatField()
    last_import_date = serializers.DateTimeField(allow_null=True)
