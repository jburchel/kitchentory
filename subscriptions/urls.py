"""
URL configuration for the subscriptions app.
"""

from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Main subscription pages
    path('', views.subscription_dashboard, name='dashboard'),
    path('upgrade/', views.upgrade_plans, name='upgrade'),
    path('manage/', views.manage_subscription, name='manage'),
    path('billing/', views.billing_history, name='billing_history'),
    
    # Stripe integration endpoints
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('create-portal-session/', views.create_customer_portal_session, name='create_portal_session'),
    path('cancel/', views.cancel_subscription_view, name='cancel_subscription'),
    
    # Checkout flow
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
    
    # Webhooks
    path('webhooks/stripe/', views.stripe_webhook, name='stripe_webhook'),
]