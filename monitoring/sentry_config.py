"""
Sentry monitoring configuration for Kitchentory.
"""

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import logging
import os


def configure_sentry():
    """Configure Sentry for error tracking and performance monitoring."""
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    environment = os.getenv('SENTRY_ENVIRONMENT', 'production')
    release = os.getenv('SENTRY_RELEASE', 'unknown')
    
    if not sentry_dsn:
        logging.warning("SENTRY_DSN not configured. Sentry monitoring disabled.")
        return
    
    # Configure logging integration
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=release,
        
        # Integrations
        integrations=[
            DjangoIntegration(
                transaction_style='url',
                middleware_spans=True,
                signals_spans=True,
                cache_spans=True,
            ),
            RedisIntegration(),
            CeleryIntegration(
                monitor_beat_tasks=True,
            ),
            sentry_logging,
            SqlalchemyIntegration(),
        ],
        
        # Performance monitoring
        traces_sample_rate=0.1,  # 10% of transactions
        profiles_sample_rate=0.1,  # 10% of transactions for profiling
        
        # Error filtering
        before_send=filter_errors,
        before_send_transaction=filter_transactions,
        
        # Additional options
        attach_stacktrace=True,
        send_default_pii=False,  # Don't send personally identifiable information
        max_breadcrumbs=50,
        
        # Custom tags
        default_integrations=True,
        auto_enabling_integrations=True,
    )
    
    # Set custom tags
    sentry_sdk.set_tag("component", "kitchentory")
    sentry_sdk.set_tag("server", os.getenv('SERVER_NAME', 'unknown'))


def filter_errors(event, hint):
    """Filter out unwanted errors before sending to Sentry."""
    
    # Skip common bot requests
    if event.get('request'):
        user_agent = event['request'].get('headers', {}).get('User-Agent', '')
        if any(bot in user_agent.lower() for bot in ['bot', 'crawler', 'spider']):
            return None
    
    # Skip certain exception types
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        
        # Skip permission denied errors for unauthorized access
        if exc_type.__name__ == 'PermissionDenied':
            return None
        
        # Skip 404 errors for known invalid paths
        if exc_type.__name__ == 'Http404':
            if hasattr(exc_value, 'args') and exc_value.args:
                if any(path in str(exc_value.args[0]) for path in [
                    'favicon.ico', '.well-known', 'robots.txt'
                ]):
                    return None
    
    # Filter sensitive data from event
    if event.get('request'):
        # Remove sensitive headers
        headers = event['request'].get('headers', {})
        sensitive_headers = ['authorization', 'cookie', 'x-api-key']
        for header in sensitive_headers:
            if header in headers:
                headers[header] = '[Filtered]'
        
        # Remove sensitive form data
        if 'data' in event['request']:
            sensitive_fields = ['password', 'token', 'secret', 'key']
            for field in sensitive_fields:
                if field in event['request']['data']:
                    event['request']['data'][field] = '[Filtered]'
    
    return event


def filter_transactions(event, hint):
    """Filter performance transactions before sending to Sentry."""
    
    # Skip health check endpoints
    transaction_name = event.get('transaction')
    if transaction_name:
        skip_patterns = ['/health/', '/ping/', '/status/']
        if any(pattern in transaction_name for pattern in skip_patterns):
            return None
    
    # Skip static file requests
    if transaction_name and any(ext in transaction_name for ext in [
        '.css', '.js', '.png', '.jpg', '.svg', '.ico'
    ]):
        return None
    
    return event


def capture_message(message, level='info', **kwargs):
    """Capture a message with additional context."""
    with sentry_sdk.configure_scope() as scope:
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_message(message, level)


def capture_exception(exception, **kwargs):
    """Capture an exception with additional context."""
    with sentry_sdk.configure_scope() as scope:
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        sentry_sdk.capture_exception(exception)


def set_user_context(user):
    """Set user context for Sentry events."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_user({
            "id": user.id,
            "username": user.username,
            "email": user.email,
        })


def set_household_context(household):
    """Set household context for Sentry events."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("household_id", household.id)
        scope.set_extra("household_name", household.name)
        scope.set_extra("household_members", household.members.count())


class SentryMiddleware:
    """Custom middleware to add Sentry context."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add request context
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("request_method", request.method)
            scope.set_extra("request_path", request.path)
            scope.set_extra("request_user_agent", request.META.get('HTTP_USER_AGENT'))
            
            # Add user context if authenticated
            if hasattr(request, 'user') and request.user.is_authenticated:
                set_user_context(request.user)
                
                # Add household context if available
                if hasattr(request.user, 'households'):
                    households = request.user.households.all()
                    if households:
                        scope.set_extra("user_households", [h.name for h in households])
        
        response = self.get_response(request)
        
        # Add response context
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("response_status", response.status_code)
        
        return response


# Performance monitoring decorators
def monitor_performance(operation_name):
    """Decorator to monitor function performance."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with sentry_sdk.start_transaction(op="function", name=operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def monitor_database_query(query_description):
    """Decorator to monitor database queries."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            with sentry_sdk.start_span(op="db", description=query_description):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Custom Sentry breadcrumbs
def add_breadcrumb(message, category='custom', level='info', data=None):
    """Add a custom breadcrumb."""
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


# Error tracking for specific operations
class InventoryErrorTracker:
    """Track inventory-related errors."""
    
    @staticmethod
    def track_barcode_scan_error(barcode, error):
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "barcode_scan")
            scope.set_extra("barcode", barcode)
            scope.set_extra("error_details", str(error))
            capture_exception(error)
    
    @staticmethod
    def track_inventory_update_error(item_id, operation, error):
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "inventory_update")
            scope.set_extra("item_id", item_id)
            scope.set_extra("operation", operation)
            capture_exception(error)


class RecipeErrorTracker:
    """Track recipe-related errors."""
    
    @staticmethod
    def track_recipe_import_error(url, error):
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "recipe_import")
            scope.set_extra("source_url", url)
            capture_exception(error)
    
    @staticmethod
    def track_ingredient_matching_error(recipe_id, error):
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "ingredient_matching")
            scope.set_extra("recipe_id", recipe_id)
            capture_exception(error)


class ShoppingErrorTracker:
    """Track shopping-related errors."""
    
    @staticmethod
    def track_list_sharing_error(list_id, user_email, error):
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "list_sharing")
            scope.set_extra("list_id", list_id)
            scope.set_extra("shared_with", user_email)
            capture_exception(error)
    
    @staticmethod
    def track_price_estimation_error(product_id, store_id, error):
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("error_type", "price_estimation")
            scope.set_extra("product_id", product_id)
            scope.set_extra("store_id", store_id)
            capture_exception(error)


# Business metrics tracking
def track_user_engagement(action, user_id, **metadata):
    """Track user engagement metrics."""
    add_breadcrumb(
        message=f"User action: {action}",
        category="user_engagement",
        level="info",
        data={
            "user_id": user_id,
            "action": action,
            **metadata
        }
    )


def track_feature_usage(feature_name, user_id, success=True, **metadata):
    """Track feature usage statistics."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("feature", feature_name)
        scope.set_tag("usage_success", success)
        scope.set_extra("user_id", user_id)
        for key, value in metadata.items():
            scope.set_extra(key, value)
        
        capture_message(
            f"Feature usage: {feature_name}",
            level="info"
        )


# Health check integration
def check_sentry_health():
    """Check if Sentry is properly configured and working."""
    try:
        # Send a test message
        capture_message("Sentry health check", level="info")
        return True
    except Exception as e:
        logging.error(f"Sentry health check failed: {e}")
        return False


# Configuration for different environments
SENTRY_CONFIG = {
    'development': {
        'traces_sample_rate': 1.0,  # Sample all transactions in dev
        'profiles_sample_rate': 1.0,
        'debug': True,
    },
    'staging': {
        'traces_sample_rate': 0.5,  # Sample 50% in staging
        'profiles_sample_rate': 0.5,
        'debug': False,
    },
    'production': {
        'traces_sample_rate': 0.1,  # Sample 10% in production
        'profiles_sample_rate': 0.1,
        'debug': False,
    }
}


def get_sentry_config(environment='production'):
    """Get Sentry configuration for specific environment."""
    return SENTRY_CONFIG.get(environment, SENTRY_CONFIG['production'])