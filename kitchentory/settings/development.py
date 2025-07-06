from .base import *

DEBUG = True

# Development-specific apps
INSTALLED_APPS += [
    'debug_toolbar',
]

# Development-specific middleware
MIDDLEWARE.insert(1, 'debug_toolbar.middleware.DebugToolbarMiddleware')

# Debug toolbar settings
INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# CORS - Allow all origins in development
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Disable HTTPS requirements in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False