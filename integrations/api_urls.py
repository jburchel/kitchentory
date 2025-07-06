from django.urls import path
from . import api_views

app_name = 'integrations_api'

urlpatterns = [
    # CSV/Excel Import
    path('csv/sample/', api_views.sample_csv, name='sample_csv'),
    path('csv/preview/', api_views.preview_import, name='preview_import'),
    path('csv/process/', api_views.process_import, name='process_import'),
    path('csv/validate-mapping/', api_views.validate_mapping, name='validate_mapping'),
    
    # Import Job Management
    path('imports/', api_views.import_history, name='import_history'),
    path('imports/<int:job_id>/', api_views.import_status, name='import_status'),
    path('imports/<int:job_id>/cancel/', api_views.cancel_import, name='cancel_import'),
    path('imports/<int:job_id>/errors/', api_views.import_errors, name='import_errors'),
    
    # Email Receipt Processing
    path('webhooks/sendgrid/', api_views.sendgrid_webhook, name='sendgrid_webhook'),
    path('webhooks/mailgun/', api_views.mailgun_webhook, name='mailgun_webhook'),
    path('webhooks/postmark/', api_views.postmark_webhook, name='postmark_webhook'),
    path('webhooks/generic/', api_views.generic_webhook, name='generic_webhook'),
    path('receipts/upload/', api_views.upload_email_receipt, name='upload_email_receipt'),
    path('receipts/', api_views.receipt_imports, name='receipt_imports'),
]