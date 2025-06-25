# Kitchentory Troubleshooting Guide

This guide helps diagnose and resolve common issues with Kitchentory.

## Table of Contents

1. [General Troubleshooting](#general-troubleshooting)
2. [Installation Issues](#installation-issues)
3. [Authentication Problems](#authentication-problems)
4. [Database Issues](#database-issues)
5. [Performance Problems](#performance-problems)
6. [Mobile/PWA Issues](#mobilepwa-issues)
7. [API Issues](#api-issues)
8. [Deployment Problems](#deployment-problems)
9. [Data Import/Export Issues](#data-importexport-issues)
10. [Browser Compatibility](#browser-compatibility)

## General Troubleshooting

### Check System Status

First, verify that all services are running:

```bash
# Check application status
sudo supervisorctl status

# Check database
sudo systemctl status postgresql

# Check Redis
sudo systemctl status redis

# Check web server
sudo systemctl status nginx
```

### Log Locations

- **Application logs**: `/opt/kitchentory/logs/`
- **Nginx logs**: `/var/log/nginx/`
- **PostgreSQL logs**: `/var/log/postgresql/`
- **System logs**: `/var/log/syslog` or `journalctl`

### Basic Health Check

Visit your application's health endpoint:
```
https://yourdomain.com/health/
```

Expected response:
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00Z",
    "services": {
        "database": "healthy",
        "redis": "healthy",
        "storage": "healthy"
    }
}
```

## Installation Issues

### Python Version Conflicts

**Problem**: `python3: command not found` or version mismatch

**Solution**:
```bash
# Check Python version
python3 --version

# Install Python 3.9+ if needed (Ubuntu)
sudo apt update
sudo apt install python3.9 python3.9-venv python3.9-dev

# Update alternatives
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1
```

### Virtual Environment Issues

**Problem**: Cannot activate virtual environment or import errors

**Solution**:
```bash
# Remove and recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip and reinstall requirements
pip install --upgrade pip
pip install -r requirements.txt
```

### Database Connection Failed

**Problem**: `django.db.utils.OperationalError: could not connect to server`

**Solution**:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql

# Check if database exists
sudo -u postgres psql -l | grep kitchentory

# Create database if missing
sudo -u postgres createdb kitchentory
```

### Permission Denied Errors

**Problem**: Permission errors when running commands

**Solution**:
```bash
# Fix ownership
sudo chown -R kitchentory:kitchentory /opt/kitchentory/

# Set correct permissions
sudo chmod -R 755 /opt/kitchentory/app/
sudo chmod -R 775 /opt/kitchentory/media/
sudo chmod -R 775 /opt/kitchentory/logs/
```

## Authentication Problems

### Cannot Login

**Problem**: Login fails with correct credentials

**Diagnosis**:
```bash
# Check user exists in database
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> User.objects.filter(username='your_username').exists()
```

**Solutions**:

1. **Password Reset**:
```bash
python manage.py changepassword username
```

2. **Check for locked accounts**:
```bash
# If using django-axes or similar
python manage.py shell
>>> from axes.models import AccessAttempt
>>> AccessAttempt.objects.filter(username='your_username')
```

3. **Create superuser**:
```bash
python manage.py createsuperuser
```

### Session Expired Issues

**Problem**: Users logged out frequently

**Check session settings** in `settings.py`:
```python
SESSION_COOKIE_AGE = 1209600  # 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
```

**Check Redis connection**:
```bash
redis-cli ping
# Should return PONG
```

### Two-Factor Authentication Problems

**Problem**: 2FA codes not working

**Solutions**:

1. **Time synchronization**:
```bash
# Ensure server time is correct
sudo ntpdate -s time.nist.gov
```

2. **Reset 2FA for user**:
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> user = get_user_model().objects.get(username='username')
>>> user.staticdevice_set.all().delete()
>>> user.totpdevice_set.all().delete()
```

## Database Issues

### Migration Errors

**Problem**: `django.db.migrations.exceptions.InconsistentMigrationHistory`

**Solution**:
```bash
# Check migration status
python manage.py showmigrations

# Reset migrations (CAUTION: Data loss possible)
python manage.py migrate --fake-initial

# Or rollback to specific migration
python manage.py migrate app_name 0001
```

### Database Lock Issues

**Problem**: `database is locked` errors

**Solution**:
```bash
# Check for long-running queries
sudo -u postgres psql kitchentory -c "SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes';"

# Kill long-running query if needed
sudo -u postgres psql kitchentory -c "SELECT pg_terminate_backend(pid);"
```

### Database Corruption

**Problem**: Data corruption or unexpected errors

**Solutions**:

1. **Check database integrity**:
```bash
sudo -u postgres psql kitchentory -c "VACUUM ANALYZE;"
```

2. **Restore from backup**:
```bash
# Stop application
sudo supervisorctl stop kitchentory

# Restore database
sudo -u postgres dropdb kitchentory
sudo -u postgres createdb kitchentory
gunzip -c backup.sql.gz | sudo -u postgres psql kitchentory

# Restart application
sudo supervisorctl start kitchentory
```

### Slow Query Performance

**Problem**: Application responds slowly

**Diagnosis**:
```sql
-- Enable query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;
SELECT pg_reload_conf();

-- Check slow queries
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC LIMIT 10;
```

**Solutions**:
```sql
-- Add missing indexes
CREATE INDEX CONCURRENTLY idx_inventory_expiry ON inventory_inventoryitem(expiration_date);

-- Update table statistics
ANALYZE;
```

## Performance Problems

### High Memory Usage

**Problem**: Application consuming too much memory

**Diagnosis**:
```bash
# Check memory usage
free -h
ps aux | grep gunicorn | head -5

# Check for memory leaks
python manage.py shell
>>> import gc
>>> gc.collect()
>>> len(gc.get_objects())
```

**Solutions**:

1. **Adjust Gunicorn workers**:
```python
# gunicorn.conf.py
workers = 2  # Reduce if memory constrained
max_requests = 1000
max_requests_jitter = 50
```

2. **Enable database connection pooling**:
```python
# settings.py
DATABASES = {
    'default': {
        # ... other settings
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'MAX_CONNS': 20
        }
    }
}
```

### High CPU Usage

**Problem**: CPU usage consistently high

**Diagnosis**:
```bash
# Check process CPU usage
top -p $(pgrep -f gunicorn)

# Profile Python code
python manage.py shell
>>> import cProfile
>>> cProfile.run('your_problematic_code_here')
```

**Solutions**:

1. **Optimize database queries**:
```python
# Use select_related for foreign keys
items = InventoryItem.objects.select_related('product', 'location')

# Use prefetch_related for reverse foreign keys
households = Household.objects.prefetch_related('members')

# Add database indexes
class Meta:
    indexes = [
        models.Index(fields=['expiration_date']),
        models.Index(fields=['created_at']),
    ]
```

2. **Implement caching**:
```python
from django.core.cache import cache

def get_inventory_stats(household_id):
    cache_key = f'inventory_stats_{household_id}'
    stats = cache.get(cache_key)
    if stats is None:
        stats = calculate_inventory_stats(household_id)
        cache.set(cache_key, stats, 300)  # Cache for 5 minutes
    return stats
```

### Slow Page Load Times

**Problem**: Pages take too long to load

**Solutions**:

1. **Enable compression**:
```nginx
# In Nginx config
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

2. **Optimize static files**:
```bash
# Minify CSS and JavaScript
npm run build:production

# Use CDN for static files
# settings.py
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

3. **Database query optimization**:
```python
# Use select_related and prefetch_related
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context['items'] = InventoryItem.objects.select_related(
        'product', 'location'
    ).prefetch_related('product__category')
    return context
```

## Mobile/PWA Issues

### PWA Not Installing

**Problem**: "Add to Home Screen" not appearing

**Check requirements**:
1. **HTTPS enabled**: PWAs require HTTPS
2. **Manifest file**: Check `/static/manifest.json`
3. **Service worker**: Check `/static/js/sw.js`

**Diagnosis**:
```javascript
// In browser console
navigator.serviceWorker.getRegistrations().then(registrations => {
    console.log('Service Workers:', registrations);
});
```

**Solutions**:

1. **Fix manifest.json**:
```json
{
    "name": "Kitchentory",
    "short_name": "Kitchentory",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#ffffff",
    "theme_color": "#3b82f6",
    "icons": [
        {
            "src": "/static/icons/icon-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        }
    ]
}
```

2. **Register service worker**:
```javascript
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/sw.js')
        .then(registration => console.log('SW registered'))
        .catch(error => console.log('SW registration failed'));
}
```

### Offline Functionality Not Working

**Problem**: App doesn't work offline

**Diagnosis**:
```javascript
// Check if offline
if (!navigator.onLine) {
    console.log('Currently offline');
}

// Check cache
caches.keys().then(cacheNames => {
    console.log('Available caches:', cacheNames);
});
```

**Solutions**:

1. **Update service worker caching**:
```javascript
const CACHE_NAME = 'kitchentory-v1';
const urlsToCache = [
    '/',
    '/static/css/app.css',
    '/static/js/app.js',
    '/inventory/',
    '/recipes/'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});
```

2. **Implement background sync**:
```javascript
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        event.waitUntil(syncData());
    }
});
```

### Mobile UI Issues

**Problem**: Interface not mobile-friendly

**Solutions**:

1. **Fix viewport meta tag**:
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

2. **Improve touch targets**:
```css
.touch-target {
    min-height: 44px;
    min-width: 44px;
    padding: 12px;
}
```

3. **Add responsive breakpoints**:
```css
/* Mobile first */
.container {
    padding: 1rem;
}

@media (min-width: 768px) {
    .container {
        padding: 2rem;
        max-width: 1200px;
        margin: 0 auto;
    }
}
```

## API Issues

### API Authentication Failing

**Problem**: API returns 401 Unauthorized

**Diagnosis**:
```bash
# Test API endpoint
curl -H "Authorization: Token your_token" https://yourdomain.com/api/inventory/

# Check token in database
python manage.py shell
>>> from rest_framework.authtoken.models import Token
>>> Token.objects.filter(key='your_token').exists()
```

**Solutions**:

1. **Generate new token**:
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> from rest_framework.authtoken.models import Token
>>> user = get_user_model().objects.get(username='username')
>>> token, created = Token.objects.get_or_create(user=user)
>>> print(token.key)
```

2. **Check authentication classes**:
```python
# In API views
class InventoryViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
```

### API Rate Limiting

**Problem**: API returns 429 Too Many Requests

**Check rate limit headers**:
```bash
curl -I -H "Authorization: Token your_token" https://yourdomain.com/api/inventory/
# Look for X-RateLimit-* headers
```

**Solutions**:

1. **Increase rate limits**:
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '2000/hour'  # Increased from 1000
    }
}
```

2. **Implement exponential backoff**:
```javascript
async function apiRequest(url, options, retries = 3) {
    try {
        const response = await fetch(url, options);
        if (response.status === 429 && retries > 0) {
            const delay = Math.pow(2, 3 - retries) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
            return apiRequest(url, options, retries - 1);
        }
        return response;
    } catch (error) {
        if (retries > 0) {
            return apiRequest(url, options, retries - 1);
        }
        throw error;
    }
}
```

### CORS Issues

**Problem**: Browser blocks API requests

**Check CORS headers**:
```bash
curl -H "Origin: https://yourdomain.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     https://yourdomain.com/api/inventory/
```

**Solutions**:

1. **Configure CORS settings**:
```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]

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
```

## Deployment Problems

### Service Won't Start

**Problem**: Gunicorn or other services fail to start

**Check logs**:
```bash
# Supervisor logs
sudo tail -f /var/log/supervisor/supervisord.log

# Application logs
sudo tail -f /opt/kitchentory/logs/gunicorn-error.log

# System logs
sudo journalctl -u supervisor -f
```

**Common solutions**:

1. **Fix file permissions**:
```bash
sudo chown -R kitchentory:kitchentory /opt/kitchentory/
```

2. **Check Python path**:
```bash
# Test if app can be imported
cd /opt/kitchentory/app
/opt/kitchentory/venv/bin/python -c "import kitchentory.wsgi"
```

3. **Verify environment variables**:
```bash
sudo -u kitchentory env | grep DATABASE_URL
```

### SSL Certificate Issues

**Problem**: HTTPS not working or certificate expired

**Check certificate status**:
```bash
# Check certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check Certbot certificates
sudo certbot certificates
```

**Solutions**:

1. **Renew certificate**:
```bash
sudo certbot renew --dry-run
sudo certbot renew
sudo systemctl restart nginx
```

2. **Fix Nginx configuration**:
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
}
```

### Static Files Not Loading

**Problem**: CSS/JS files return 404

**Check static files**:
```bash
# Verify static files collected
ls -la /opt/kitchentory/static/

# Check Nginx configuration
sudo nginx -t
```

**Solutions**:

1. **Collect static files**:
```bash
python manage.py collectstatic --noinput
```

2. **Fix Nginx static file serving**:
```nginx
location /static/ {
    alias /opt/kitchentory/static/;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Data Import/Export Issues

### CSV Import Errors

**Problem**: Data import fails with encoding or format errors

**Common solutions**:

1. **Fix encoding issues**:
```python
# In import script
import chardet

with open('data.csv', 'rb') as f:
    encoding = chardet.detect(f.read())['encoding']

with open('data.csv', 'r', encoding=encoding) as f:
    # Process file
```

2. **Handle malformed CSV**:
```python
import csv

try:
    with open('data.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Process row with validation
            clean_row = {k: v.strip() for k, v in row.items() if v}
except csv.Error as e:
    print(f"CSV error: {e}")
```

### Barcode Recognition Issues

**Problem**: Barcode scanning not working

**Solutions**:

1. **Camera permissions**:
```javascript
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        // Camera access granted
    })
    .catch(error => {
        console.error('Camera access denied:', error);
    });
```

2. **Improve barcode detection**:
```javascript
// Use better lighting and focus
const constraints = {
    video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: { ideal: 'environment' },
        focusMode: { ideal: 'macro' }
    }
};
```

## Browser Compatibility

### Internet Explorer Issues

**Problem**: Application doesn't work in older browsers

**Solutions**:

1. **Add polyfills**:
```html
<script src="https://polyfill.io/v3/polyfill.min.js?features=es6,fetch"></script>
```

2. **Graceful degradation**:
```javascript
// Check for modern features
if ('fetch' in window && 'Promise' in window) {
    // Use modern code
} else {
    // Fallback for older browsers
}
```

### Safari Issues

**Problem**: PWA features not working in Safari

**Solutions**:

1. **Add Safari-specific meta tags**:
```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
```

2. **Fix iOS viewport issues**:
```css
/* Fix iOS zoom on input focus */
input[type="text"],
input[type="email"],
textarea {
    font-size: 16px;
}
```

## Emergency Recovery

### Complete System Recovery

If the system is completely broken:

1. **Stop all services**:
```bash
sudo supervisorctl stop all
sudo systemctl stop nginx
```

2. **Restore from backup**:
```bash
# Database
sudo -u postgres dropdb kitchentory
sudo -u postgres createdb kitchentory
gunzip -c /opt/kitchentory/backups/latest_db.sql.gz | sudo -u postgres psql kitchentory

# Media files
sudo rm -rf /opt/kitchentory/media/*
sudo tar -xzf /opt/kitchentory/backups/latest_media.tar.gz -C /opt/kitchentory/

# Application code
cd /opt/kitchentory/app
sudo -u kitchentory git reset --hard HEAD
```

3. **Restart services**:
```bash
sudo systemctl start nginx
sudo supervisorctl start all
```

### Contact Support

If issues persist:

- **Email**: support@kitchentory.com
- **GitHub Issues**: https://github.com/kitchentory/kitchentory/issues
- **Discord**: Join our support channel
- **Documentation**: https://docs.kitchentory.com

Include in your support request:
- Error messages and logs
- Steps to reproduce
- System information
- Screenshots if applicable