import json
import logging
import hmac
import hashlib
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import (
    ImportJob,
    ImportSource,
    ImportStatus,
    ParsedReceiptItem,
    EmailReceiptConfig,
)
from .enhanced_receipt_parser import EnhancedReceiptParser
from .email_webhook import EmailWebhookService, process_raw_email
from accounts.models import Household

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def email_webhook(request):
    """
    Webhook endpoint for receiving email receipts
    Supports multiple email services (SendGrid, Mailgun, etc.)
    """
    try:
        # Determine email service type
        service_type = request.headers.get("User-Agent", "").lower()

        if "sendgrid" in service_type:
            return handle_sendgrid_webhook(request)
        elif "mailgun" in service_type:
            return handle_mailgun_webhook(request)
        else:
            # Generic email webhook format
            return handle_generic_webhook(request)

    except Exception as e:
        logger.error(f"Email webhook error: {e}")
        return JsonResponse({"error": "Processing failed"}, status=500)


def handle_sendgrid_webhook(request):
    """Handle SendGrid inbound email webhook"""
    try:
        data = json.loads(request.body)

        for email in data:
            sender = email.get("from")
            subject = email.get("subject", "")
            text_body = email.get("text", "")
            html_body = email.get("html", "")

            # Use text body, fallback to HTML
            body = text_body or html_body

            # Find household by email address
            to_email = email.get("to")
            household = find_household_by_email(to_email)

            if household:
                process_receipt_email(household, sender, subject, body)

        return JsonResponse({"status": "success"})

    except Exception as e:
        logger.error(f"SendGrid webhook error: {e}")
        return JsonResponse({"error": "Invalid request"}, status=400)


def handle_mailgun_webhook(request):
    """Handle Mailgun inbound email webhook"""
    try:
        sender = request.POST.get("sender")
        subject = request.POST.get("subject", "")
        body = request.POST.get("body-plain", "") or request.POST.get("body-html", "")
        to_email = request.POST.get("recipient")

        # Verify webhook signature
        if not verify_mailgun_signature(request):
            return JsonResponse({"error": "Invalid signature"}, status=401)

        household = find_household_by_email(to_email)
        if household:
            process_receipt_email(household, sender, subject, body)

        return JsonResponse({"status": "success"})

    except Exception as e:
        logger.error(f"Mailgun webhook error: {e}")
        return JsonResponse({"error": "Invalid request"}, status=400)


def handle_generic_webhook(request):
    """Handle generic email webhook format"""
    try:
        data = json.loads(request.body)

        sender = data.get("from") or data.get("sender")
        subject = data.get("subject", "")
        body = data.get("text") or data.get("body") or data.get("content")
        to_email = data.get("to") or data.get("recipient")

        household = find_household_by_email(to_email)
        if household:
            process_receipt_email(household, sender, subject, body)

        return JsonResponse({"status": "success"})

    except Exception as e:
        logger.error(f"Generic webhook error: {e}")
        return JsonResponse({"error": "Invalid request"}, status=400)


def find_household_by_email(email_address):
    """Find household by receipt email address"""
    try:
        config = EmailReceiptConfig.objects.get(email_address=email_address)
        return config.household
    except EmailReceiptConfig.DoesNotExist:
        logger.warning(f"No household found for email: {email_address}")
        return None


def process_receipt_email(household, sender, subject, body):
    """Process a receipt email and create import job"""
    try:
        # Create import job
        import_job = ImportJob.objects.create(
            household=household,
            user=household.created_by,  # Use household owner as user
            source=ImportSource.EMAIL_RECEIPT,
            status=ImportStatus.PROCESSING,
            email_data={
                "sender": sender,
                "subject": subject,
                "body": body[:10000],  # Limit body size
            },
        )

        # Parse receipt
        parser = ReceiptParser()
        receipt_data = parser.parse_receipt(
            {"sender": sender, "subject": subject, "body": body}
        )

        # Store parsed data
        import_job.raw_data = receipt_data
        import_job.total_items = len(receipt_data.get("items", []))
        import_job.save()

        # Create parsed items
        for item_data in receipt_data.get("items", []):
            ParsedReceiptItem.objects.create(
                import_job=import_job,
                raw_text=item_data.get("raw_text", ""),
                line_number=item_data.get("line_number"),
                name=item_data.get("name", ""),
                quantity=item_data.get("quantity", 1),
                unit=item_data.get("unit", "item"),
                price=item_data.get("price"),
                confidence_score=item_data.get("confidence_score", 0),
                store_name=receipt_data.get("store", ""),
                purchase_date=receipt_data.get("purchase_date"),
            )

        # Check if auto-approval is enabled
        try:
            config = EmailReceiptConfig.objects.get(household=household)
            if (
                config.auto_approve
                and receipt_data.get("confidence_score", 0)
                >= config.confidence_threshold
            ):
                # Auto-approve and process
                import_service = ImportService()
                import_service.process_import_job(import_job.id)
        except EmailReceiptConfig.DoesNotExist:
            pass

        # Update status
        import_job.status = ImportStatus.PENDING
        import_job.save()

        logger.info(
            f"Processed receipt email for household {household.name}: {import_job.id}"
        )

    except Exception as e:
        logger.error(f"Error processing receipt email: {e}")
        if "import_job" in locals():
            import_job.status = ImportStatus.FAILED
            import_job.errors = {"error": str(e)}
            import_job.save()


def verify_mailgun_signature(request):
    """Verify Mailgun webhook signature"""
    # This would use your Mailgun API key
    # For now, return True (implement proper verification in production)
    return True


# Web views for managing imports
@login_required
def import_dashboard(request):
    """Dashboard showing all import jobs"""
    jobs = ImportJob.objects.filter(household=request.user.household).order_by(
        "-created_at"
    )[:20]

    return render(request, "integrations/dashboard.html", {"jobs": jobs})


@login_required
def import_detail(request, job_id):
    """Detail view for a specific import job"""
    job = get_object_or_404(ImportJob, id=job_id, household=request.user.household)

    parsed_items = job.parsed_items.all()

    return render(
        request,
        "integrations/import_detail.html",
        {"job": job, "parsed_items": parsed_items},
    )


@login_required
def approve_import(request, job_id):
    """Approve and process an import job"""
    job = get_object_or_404(
        ImportJob,
        id=job_id,
        household=request.user.household,
        status=ImportStatus.PENDING,
    )

    if request.method == "POST":
        try:
            # Get selected items to approve
            selected_items = request.POST.getlist("approve_items")

            # Mark selected items as approved
            job.parsed_items.filter(id__in=selected_items).update(is_approved=True)

            # Process the job
            import_service = ImportService()
            result = import_service.process_import_job(job.id)

            if result["success"]:
                messages.success(
                    request, f"Successfully imported {result['created']} items!"
                )
            else:
                messages.error(
                    request, f"Import failed: {result.get('error', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error approving import {job_id}: {e}")
            messages.error(request, "Failed to process import")

        return redirect("integrations:import_detail", job_id=job.id)

    return redirect("integrations:import_detail", job_id=job.id)


@login_required
def email_config(request):
    """Configure email receipt settings"""
    config, created = EmailReceiptConfig.objects.get_or_create(
        household=request.user.household,
        defaults={
            "email_address": f"{request.user.household.invite_code}@receipts.kitchentory.com"
        },
    )

    if request.method == "POST":
        config.auto_approve = request.POST.get("auto_approve") == "on"
        config.confidence_threshold = float(
            request.POST.get("confidence_threshold", 0.8)
        )

        # Update store mappings
        store_mappings = {}
        for key, value in request.POST.items():
            if key.startswith("store_"):
                email_pattern = key.replace("store_", "")
                if value:
                    store_mappings[email_pattern] = value
        config.store_mappings = store_mappings

        config.save()
        messages.success(request, "Email settings updated!")

    return render(request, "integrations/email_config.html", {"config": config})


@login_required
def browser_extension_guide(request):
    """Browser extension installation and setup guide"""
    return render(request, "integrations/browser_extension.html")


@login_required
def csv_import_view(request):
    """Main CSV/Excel import interface"""
    return render(request, "integrations/import.html")


@login_required
def import_history_view(request):
    """View import history for the household"""

    import_jobs = ImportJob.objects.filter(household=request.user.household).order_by(
        "-created_at"
    )[:50]

    # Add success rate calculation
    for job in import_jobs:
        if job.total_items > 0:
            job.success_rate = round((job.created_items / job.total_items) * 100, 1)
        else:
            job.success_rate = 0

    context = {"import_jobs": import_jobs}

    return render(request, "integrations/history.html", context)


@login_required
def import_detail_view(request, job_id):
    """View details of a specific import job"""

    import_job = get_object_or_404(
        ImportJob, id=job_id, household=request.user.household
    )

    # Calculate success rate
    if import_job.total_items > 0:
        import_job.success_rate = round(
            (import_job.created_items / import_job.total_items) * 100, 1
        )
    else:
        import_job.success_rate = 0

    # Calculate duration
    if import_job.completed_at:
        duration = (import_job.completed_at - import_job.created_at).total_seconds()
        import_job.duration_seconds = round(duration, 1)
    else:
        import_job.duration_seconds = None

    context = {
        "import_job": import_job,
        "parsed_items": import_job.parsed_items.all()[:200],  # Limit for performance
    }

    return render(request, "integrations/detail.html", context)


# API endpoints
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def csv_upload(request):
    """Upload and parse CSV file"""
    try:
        if "file" not in request.FILES:
            return Response(
                {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        file = request.FILES["file"]

        # Validate file type
        if not file.name.endswith((".csv", ".xlsx", ".xls")):
            return Response(
                {"error": "Invalid file type"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Create import job
        import_job = ImportJob.objects.create(
            household=request.user.household,
            user=request.user,
            source=ImportSource.CSV_UPLOAD,
            status=ImportStatus.PROCESSING,
            file_path=file.name,
        )

        # Process file
        import_service = ImportService()
        result = import_service.process_csv_file(import_job.id, file)

        return Response(
            {
                "job_id": import_job.id,
                "status": "processing",
                "items_found": result.get("items_found", 0),
            }
        )

    except Exception as e:
        logger.error(f"CSV upload error: {e}")
        return Response(
            {"error": "Upload failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_status(request, job_id):
    """Get status of an import job"""
    try:
        job = ImportJob.objects.get(id=job_id, household=request.user.household)

        return Response(
            {
                "id": job.id,
                "status": job.status,
                "source": job.source,
                "total_items": job.total_items,
                "processed_items": job.processed_items,
                "created_items": job.created_items,
                "failed_items": job.failed_items,
                "errors": job.errors,
                "created_at": job.created_at.isoformat(),
                "completed_at": (
                    job.completed_at.isoformat() if job.completed_at else None
                ),
            }
        )

    except ImportJob.DoesNotExist:
        return Response(
            {"error": "Import job not found"}, status=status.HTTP_404_NOT_FOUND
        )


# Enhanced Email Receipt Views


@login_required
def receipt_review(request, job_id):
    """Review parsed receipt items before adding to inventory"""

    import_job = get_object_or_404(
        ImportJob,
        id=job_id,
        household=request.user.household,
        source=ImportSource.EMAIL_RECEIPT,
    )

    if request.method == "POST":
        return _process_receipt_review(request, import_job)

    context = {
        "import_job": import_job,
        "parsed_items": import_job.parsed_items.all(),
        "metadata": import_job.raw_data or {},
        "can_edit": import_job.status
        in [ImportStatus.PENDING, ImportStatus.PROCESSING],
    }

    return render(request, "integrations/receipt_review.html", context)


@login_required
def email_setup_guide(request):
    """Guide for setting up email forwarding for receipt processing"""

    context = {
        "webhook_urls": _get_webhook_urls(request),
        "setup_instructions": _get_detailed_setup_instructions(),
        "supported_stores": _get_supported_stores(),
    }

    return render(request, "integrations/email_setup.html", context)


@login_required
def manual_email_upload(request):
    """Manual email upload interface for testing"""

    if request.method == "POST":
        email_content = request.POST.get("email_content", "")

        if not email_content:
            messages.error(request, "Please provide email content")
            return render(request, "integrations/manual_upload.html")

        try:
            result = process_raw_email(email_content, request.user.email)

            if result["success"]:
                messages.success(
                    request,
                    f"Email processed successfully! Found {result.get('items_found', 0)} items. "
                    f"Confidence: {result.get('confidence_score', 0):.0%}",
                )
                return redirect(
                    "integrations:receipt_review", job_id=result["import_job_id"]
                )
            else:
                messages.error(
                    request,
                    f"Processing failed: {result.get('error', 'Unknown error')}",
                )

        except Exception as e:
            logger.error(f"Manual email upload error: {e}")
            messages.error(request, f"Upload failed: {str(e)}")

    return render(request, "integrations/manual_upload.html")


@login_required
def approve_receipt(request, job_id):
    """Approve receipt items and add to inventory"""

    import_job = get_object_or_404(
        ImportJob,
        id=job_id,
        household=request.user.household,
        source=ImportSource.EMAIL_RECEIPT,
    )

    if import_job.status != ImportStatus.PENDING:
        messages.error(request, "Receipt has already been processed")
        return redirect("integrations:receipt_review", job_id=job_id)

    try:
        webhook_service = EmailWebhookService()
        webhook_service._auto_process_receipt(import_job)

        import_job.status = ImportStatus.COMPLETED
        import_job.save()

        created_count = (
            import_job.raw_data.get("auto_created_items", 0)
            if import_job.raw_data
            else 0
        )
        messages.success(
            request, f"Receipt approved! Created {created_count} inventory items."
        )

    except Exception as e:
        logger.error(f"Receipt approval failed: {e}")
        messages.error(request, f"Approval failed: {str(e)}")

    return redirect("integrations:receipt_review", job_id=job_id)


@login_required
def reject_receipt(request, job_id):
    """Reject receipt import"""

    import_job = get_object_or_404(
        ImportJob,
        id=job_id,
        household=request.user.household,
        source=ImportSource.EMAIL_RECEIPT,
    )

    import_job.status = ImportStatus.CANCELLED
    import_job.save()

    messages.info(request, "Receipt import has been cancelled")
    return redirect("integrations:import_dashboard")


def _process_receipt_review(request, import_job):
    """Process receipt review form submission"""

    # Get selected items
    selected_items = request.POST.getlist("selected_items")

    if not selected_items:
        messages.error(request, "Please select at least one item to import")
        return redirect("integrations:receipt_review", job_id=import_job.id)

    try:
        from inventory.models import InventoryItem, Category, StorageLocation

        # Get or create default category and location
        default_category, _ = Category.objects.get_or_create(
            name="Email Receipt Items", defaults={"household": import_job.household}
        )

        default_location, _ = StorageLocation.objects.get_or_create(
            name="Kitchen", defaults={"household": import_job.household}
        )

        created_count = 0

        for item_id in selected_items:
            try:
                receipt_item = import_job.parsed_items.get(id=int(item_id))

                # Get custom values from form
                name = request.POST.get(f"name_{item_id}", receipt_item.name)
                quantity = float(
                    request.POST.get(f"quantity_{item_id}", receipt_item.quantity)
                )
                unit = request.POST.get(f"unit_{item_id}", receipt_item.unit)
                category_name = request.POST.get(
                    f"category_{item_id}", default_category.name
                )
                location_name = request.POST.get(
                    f"location_{item_id}", default_location.name
                )

                # Get or create category and location
                category, _ = Category.objects.get_or_create(
                    name=category_name, defaults={"household": import_job.household}
                )

                location, _ = StorageLocation.objects.get_or_create(
                    name=location_name, defaults={"household": import_job.household}
                )

                # Create inventory item
                inventory_item = InventoryItem.objects.create(
                    household=import_job.household,
                    name=name,
                    brand=receipt_item.brand or "",
                    quantity=quantity,
                    unit=unit,
                    category=category,
                    storage_location=location,
                    purchase_price=receipt_item.price,
                    notes=f"Imported from {import_job.raw_data.get('store_name', 'email receipt') if import_job.raw_data else 'email receipt'}",
                )

                # Link receipt item to inventory item
                receipt_item.inventory_item = inventory_item
                receipt_item.save()

                created_count += 1

            except Exception as e:
                logger.error(f"Error creating inventory item {item_id}: {e}")
                continue

        # Update import job
        import_job.status = ImportStatus.COMPLETED
        if not import_job.raw_data:
            import_job.raw_data = {}
        import_job.raw_data["manual_created_items"] = created_count
        import_job.save()

        messages.success(
            request, f"Successfully imported {created_count} items to your inventory!"
        )

        return redirect("inventory:dashboard")

    except Exception as e:
        logger.error(f"Receipt processing error: {e}")
        messages.error(request, f"Import failed: {str(e)}")
        return redirect("integrations:receipt_review", job_id=import_job.id)


def _get_webhook_urls(request):
    """Get webhook URLs for email service setup"""
    base_url = request.build_absolute_uri("/")[:-1]  # Remove trailing slash

    return {
        "sendgrid": f"{base_url}/api/integrations/webhooks/sendgrid/",
        "mailgun": f"{base_url}/api/integrations/webhooks/mailgun/",
        "postmark": f"{base_url}/api/integrations/webhooks/postmark/",
        "generic": f"{base_url}/api/integrations/webhooks/generic/",
    }


def _get_detailed_setup_instructions():
    """Get detailed setup instructions for each service"""
    return {
        "sendgrid": {
            "title": "SendGrid Inbound Parse",
            "steps": [
                "Log into your SendGrid account",
                "Go to Settings > Inbound Parse",
                "Add a new hostname (e.g., receipts.yourdomain.com)",
                "Set the destination URL to our SendGrid webhook",
                "Configure your DNS to point to SendGrid",
                "Test with a receipt email",
            ],
        },
        "mailgun": {
            "title": "Mailgun Routes",
            "steps": [
                "Log into your Mailgun account",
                "Go to Receiving > Routes",
                "Create a new route matching receipt emails",
                "Set action to forward to our Mailgun webhook",
                "Configure your email forwarding",
                "Test with a sample receipt",
            ],
        },
        "gmail_forwarding": {
            "title": "Gmail Auto-Forward Setup",
            "steps": [
                "Open Gmail Settings > Forwarding and POP/IMAP",
                "Add a forwarding address (we'll provide one)",
                "Create filters for receipt emails (from stores)",
                "Set filters to forward to our processing email",
                "Test with a receipt from a supported store",
            ],
        },
    }


def _get_supported_stores():
    """Get list of supported stores"""
    return [
        {"name": "Instacart", "status": "full", "confidence": 95},
        {"name": "Amazon Fresh", "status": "full", "confidence": 90},
        {"name": "Walmart", "status": "full", "confidence": 85},
        {"name": "Target", "status": "beta", "confidence": 80},
        {"name": "Kroger", "status": "beta", "confidence": 75},
        {"name": "Safeway", "status": "beta", "confidence": 75},
        {"name": "Costco", "status": "beta", "confidence": 70},
        {"name": "Whole Foods", "status": "beta", "confidence": 80},
        {"name": "Generic Store", "status": "basic", "confidence": 60},
    ]
