from django.urls import path
from . import views

app_name = 'integrations'

urlpatterns = [
    # Import management
    path('', views.import_dashboard, name='dashboard'),
    path('import/', views.csv_import_view, name='csv_import'),
    path('import/history/', views.import_history_view, name='import_history'),
    path('import/<int:job_id>/', views.import_detail_view, name='import_detail'),
    path('import/<int:job_id>/approve/', views.approve_import, name='approve_import'),
    
    # Email configuration
    path('email/config/', views.email_config, name='email_config'),
    
    # Browser Extension
    path('browser-extension/', views.browser_extension_guide, name='browser_extension'),
    
    # Webhooks (no auth required)
    path('webhook/email/', views.email_webhook, name='email_webhook'),
]