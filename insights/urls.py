"""
URL configuration for the insights app.
"""

from django.urls import path
from . import views

app_name = 'insights'

urlpatterns = [
    path('', views.analytics_dashboard, name='dashboard'),
    path('advanced/', views.advanced_analytics, name='advanced'),
    path('export/', views.export_data, name='export'),
]