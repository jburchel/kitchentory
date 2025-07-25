# Generated by Django 5.2.3 on 2025-06-26 00:03

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailReceiptConfig",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "email_address",
                    models.EmailField(
                        help_text="Dedicated email for receipt forwarding",
                        max_length=254,
                    ),
                ),
                ("webhook_secret", models.CharField(blank=True, max_length=100)),
                (
                    "auto_approve",
                    models.BooleanField(
                        default=False,
                        help_text="Automatically add items without review",
                    ),
                ),
                (
                    "confidence_threshold",
                    models.FloatField(
                        default=0.8, help_text="Minimum confidence for auto-approval"
                    ),
                ),
                (
                    "store_mappings",
                    models.JSONField(
                        default=dict, help_text="Map email senders to store names"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "household",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.household",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ImportJob",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "source",
                    models.CharField(
                        choices=[
                            ("email", "Email Receipt"),
                            ("csv", "CSV Upload"),
                            ("browser", "Browser Extension"),
                            ("api", "Store API"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending Review"),
                            ("processing", "Processing"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("email_data", models.JSONField(blank=True, null=True)),
                ("file_path", models.CharField(blank=True, max_length=500)),
                ("store_data", models.JSONField(blank=True, null=True)),
                ("total_items", models.IntegerField(default=0)),
                ("processed_items", models.IntegerField(default=0)),
                ("created_items", models.IntegerField(default=0)),
                ("failed_items", models.IntegerField(default=0)),
                ("raw_data", models.JSONField(blank=True, null=True)),
                ("validated_data", models.JSONField(blank=True, null=True)),
                ("errors", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.household",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ParsedReceiptItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("raw_text", models.TextField(blank=True)),
                ("line_number", models.IntegerField(blank=True, null=True)),
                ("name", models.CharField(max_length=200)),
                ("brand", models.CharField(blank=True, max_length=100)),
                (
                    "quantity",
                    models.DecimalField(decimal_places=3, default=1, max_digits=10),
                ),
                ("unit", models.CharField(default="item", max_length=20)),
                (
                    "price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=8, null=True
                    ),
                ),
                ("confidence_score", models.FloatField(blank=True, null=True)),
                ("suggested_product_id", models.IntegerField(blank=True, null=True)),
                ("suggested_category", models.CharField(blank=True, max_length=100)),
                ("is_processed", models.BooleanField(default=False)),
                ("is_approved", models.BooleanField(default=False)),
                (
                    "created_inventory_item_id",
                    models.IntegerField(blank=True, null=True),
                ),
                ("store_name", models.CharField(blank=True, max_length=100)),
                ("purchase_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "import_job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parsed_items",
                        to="integrations.importjob",
                    ),
                ),
            ],
            options={
                "ordering": ["line_number", "name"],
            },
        ),
        migrations.CreateModel(
            name="StoreAPICredential",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("store_name", models.CharField(max_length=100)),
                ("api_key", models.TextField(blank=True)),
                ("api_secret", models.TextField(blank=True)),
                ("access_token", models.TextField(blank=True)),
                ("refresh_token", models.TextField(blank=True)),
                ("auto_sync", models.BooleanField(default=False)),
                ("sync_frequency", models.CharField(default="daily", max_length=20)),
                ("last_sync", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "household",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.household",
                    ),
                ),
            ],
            options={
                "unique_together": {("household", "store_name")},
            },
        ),
    ]
