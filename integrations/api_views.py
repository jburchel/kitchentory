"""
API views for integrations app
Handles CSV import, preview, and import job status
"""

import logging
import json
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.core.files.uploadedfile import UploadedFile
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .csv_import import CSVImportService, ImportMapping
from .email_webhook import EmailWebhookService, process_raw_email
from .models import ImportJob
from .serializers import ImportJobSerializer, ImportPreviewSerializer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def sample_csv(request):
    """Download a sample CSV file for import"""
    
    try:
        csv_content = CSVImportService.get_sample_csv()
        
        response = HttpResponse(csv_content, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="kitchentory_sample_import.csv"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating sample CSV: {e}")
        return Response({
            'error': 'Could not generate sample CSV'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def preview_import(request):
    """Preview CSV/Excel import before processing"""
    
    if 'file' not in request.FILES:
        return Response({
            'error': 'No file provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    uploaded_file = request.FILES['file']
    
    try:
        # Initialize import service
        import_service = CSVImportService(
            household=request.user.household,
            user=request.user
        )
        
        # Validate file
        is_valid, message = import_service.validate_file(uploaded_file)
        if not is_valid:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get column mapping from request if provided
        mapping_data = request.data.get('mapping', {})
        mapping = ImportMapping(**mapping_data) if mapping_data else None
        
        # Generate preview
        preview = import_service.preview_import(uploaded_file, mapping)
        
        # Serialize response
        serializer = ImportPreviewSerializer(preview)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error previewing import: {e}")
        return Response({
            'error': f'Preview failed: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_import(request):
    """Process CSV/Excel import with confirmed mapping"""
    
    if 'file' not in request.FILES:
        return Response({
            'error': 'No file provided'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    mapping_data = request.data.get('mapping', {})
    if not mapping_data:
        return Response({
            'error': 'Column mapping required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    uploaded_file = request.FILES['file']
    
    try:
        # Initialize import service
        import_service = CSVImportService(
            household=request.user.household,
            user=request.user
        )
        
        # Validate file
        is_valid, message = import_service.validate_file(uploaded_file)
        if not is_valid:
            return Response({
                'error': message
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create mapping object
        mapping = ImportMapping(**mapping_data)
        
        # Process import
        import_job = import_service.process_import(uploaded_file, mapping)
        
        # Serialize response
        serializer = ImportJobSerializer(import_job)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error processing import: {e}")
        return Response({
            'error': f'Import failed: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def import_status(request, job_id):
    """Get status of an import job"""
    
    try:
        import_job = get_object_or_404(
            ImportJob,
            id=job_id,
            household=request.user.household
        )
        
        serializer = ImportJobSerializer(import_job)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting import status: {e}")
        return Response({
            'error': 'Import job not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def import_history(request):
    """Get import history for the user's household"""
    
    try:
        import_jobs = ImportJob.objects.filter(
            household=request.user.household
        ).order_by('-created_at')[:50]  # Last 50 imports
        
        serializer = ImportJobSerializer(import_jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting import history: {e}")
        return Response({
            'error': 'Could not retrieve import history'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_import(request, job_id):
    """Cancel a pending import job"""
    
    try:
        import_job = get_object_or_404(
            ImportJob,
            id=job_id,
            household=request.user.household
        )
        
        if import_job.status == 'processing':
            return Response({
                'error': 'Cannot cancel import that is already processing'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if import_job.status in ['completed', 'failed', 'cancelled']:
            return Response({
                'error': 'Import job has already finished'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        import_job.status = 'cancelled'
        import_job.save()
        
        serializer = ImportJobSerializer(import_job)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error cancelling import: {e}")
        return Response({
            'error': 'Could not cancel import job'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def import_errors(request, job_id):
    """Get detailed errors for an import job"""
    
    try:
        import_job = get_object_or_404(
            ImportJob,
            id=job_id,
            household=request.user.household
        )
        
        errors = import_job.errors or []
        
        return Response({
            'job_id': import_job.id,
            'total_errors': len(errors),
            'errors': errors
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting import errors: {e}")
        return Response({
            'error': 'Could not retrieve import errors'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_mapping(request):
    """Validate column mapping configuration"""
    
    mapping_data = request.data.get('mapping', {})
    column_names = request.data.get('columns', [])
    
    if not mapping_data:
        return Response({
            'error': 'Mapping data required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create mapping object
        mapping = ImportMapping(**mapping_data)
        
        # Validate mapping
        errors = []
        warnings = []
        
        # Check required fields
        if not mapping.name:
            errors.append("Product name column is required")
        
        # Check if mapped columns exist
        for field, column in mapping_data.items():
            if column and column not in column_names:
                errors.append(f"Column '{column}' mapped to '{field}' does not exist")
        
        # Warnings for missing optional but recommended fields
        if not mapping.quantity:
            warnings.append("Quantity column not mapped - will default to 1")
        
        if not mapping.unit:
            warnings.append("Unit column not mapped - will default to 'item'")
        
        return Response({
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'mapping': mapping_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error validating mapping: {e}")
        return Response({
            'error': f'Mapping validation failed: {str(e)}'
        }, status=status.HTTP_400_BAD_REQUEST)


# Email Receipt Webhook Endpoints

@csrf_exempt
@require_http_methods(["POST"])
def sendgrid_webhook(request):
    """Handle SendGrid email webhook for receipt processing"""
    
    try:
        # Parse JSON payload
        payload = json.loads(request.body.decode('utf-8'))
        headers = dict(request.headers)
        
        # Process webhook
        webhook_service = EmailWebhookService()
        result = webhook_service.process_webhook('sendgrid', payload, headers)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'import_job_id': result.get('import_job_id'),
                'items_found': result.get('items_found', 0)
            }, status=200)
        else:
            return JsonResponse({
                'status': 'error',
                'message': result.get('error', 'Processing failed')
            }, status=400)
            
    except Exception as e:
        logger.error(f"SendGrid webhook error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Webhook processing failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def mailgun_webhook(request):
    """Handle Mailgun email webhook for receipt processing"""
    
    try:
        # Mailgun sends form data, not JSON
        payload = dict(request.POST)
        headers = dict(request.headers)
        
        # Process webhook
        webhook_service = EmailWebhookService()
        result = webhook_service.process_webhook('mailgun', payload, headers)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'import_job_id': result.get('import_job_id'),
                'items_found': result.get('items_found', 0)
            }, status=200)
        else:
            return JsonResponse({
                'status': 'error',
                'message': result.get('error', 'Processing failed')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Mailgun webhook error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Webhook processing failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def postmark_webhook(request):
    """Handle Postmark email webhook for receipt processing"""
    
    try:
        # Parse JSON payload
        payload = json.loads(request.body.decode('utf-8'))
        headers = dict(request.headers)
        
        # Process webhook
        webhook_service = EmailWebhookService()
        result = webhook_service.process_webhook('postmark', payload, headers)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'import_job_id': result.get('import_job_id'),
                'items_found': result.get('items_found', 0)
            }, status=200)
        else:
            return JsonResponse({
                'status': 'error',
                'message': result.get('error', 'Processing failed')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Postmark webhook error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Webhook processing failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generic_webhook(request):
    """Handle generic email webhook for receipt processing"""
    
    try:
        # Try to parse as JSON first, fall back to form data
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except:
            payload = dict(request.POST)
        
        headers = dict(request.headers)
        
        # Process webhook
        webhook_service = EmailWebhookService()
        result = webhook_service.process_webhook('generic', payload, headers)
        
        if result['success']:
            return JsonResponse({
                'status': 'success',
                'import_job_id': result.get('import_job_id'),
                'items_found': result.get('items_found', 0)
            }, status=200)
        else:
            return JsonResponse({
                'status': 'error',
                'message': result.get('error', 'Processing failed')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Generic webhook error: {e}")
        return JsonResponse({
            'status': 'error',
            'message': 'Webhook processing failed'
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_email_receipt(request):
    """Upload raw email content for receipt processing"""
    
    raw_email = request.data.get('email_content', '')
    if not raw_email:
        return Response({
            'error': 'Email content required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Process raw email
        result = process_raw_email(raw_email, request.user.email)
        
        if result['success']:
            return Response({
                'success': True,
                'import_job_id': result.get('import_job_id'),
                'items_found': result.get('items_found', 0),
                'confidence_score': result.get('confidence_score', 0.0)
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'error': result.get('error', 'Processing failed')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Email upload error: {e}")
        return Response({
            'error': f'Email processing failed: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def receipt_imports(request):
    """Get receipt imports for the user's household"""
    
    try:
        from .models import ImportSource
        
        receipt_imports = ImportJob.objects.filter(
            household=request.user.household,
            source=ImportSource.EMAIL_RECEIPT
        ).order_by('-created_at')[:20]  # Last 20 receipt imports
        
        serializer = ImportJobSerializer(receipt_imports, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting receipt imports: {e}")
        return Response({
            'error': 'Could not retrieve receipt imports'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)