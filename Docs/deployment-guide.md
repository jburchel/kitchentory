# Kitchentory Deployment Guide

This guide covers deploying Kitchentory to production environments, including setup, configuration, and maintenance.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Database Configuration](#database-configuration)
4. [Application Deployment](#application-deployment)
5. [Web Server Configuration](#web-server-configuration)
6. [SSL/TLS Setup](#ssltls-setup)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Backup Strategy](#backup-strategy)
9. [Performance Optimization](#performance-optimization)
10. [Security Hardening](#security-hardening)
11. [Maintenance](#maintenance)
12. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4GB
- Storage: 50GB SSD
- OS: Ubuntu 20.04+ / CentOS 8+ / Amazon Linux 2

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 100GB+ SSD
- Load balancer for high availability

### Required Software

- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- Nginx 1.18+
- Supervisor (process management)
- Certbot (SSL certificates)

## Environment Setup

### 1. System Updates

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y

# CentOS/RHEL
sudo yum update -y
```

### 2. Install Dependencies

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib \
    redis-server nginx supervisor git curl

# CentOS/RHEL
sudo yum install -y python3 python3-pip postgresql postgresql-server redis nginx \
    supervisor git curl
```

### 3. Create Application User

```bash
sudo useradd --system --shell /bin/bash --home /opt/kitchentory kitchentory
sudo mkdir -p /opt/kitchentory
sudo chown kitchentory:kitchentory /opt/kitchentory
```

### 4. Clone Repository

```bash
sudo -u kitchentory git clone https://github.com/your-org/kitchentory.git /opt/kitchentory/app
cd /opt/kitchentory/app
```

### 5. Create Virtual Environment

```bash
sudo -u kitchentory python3 -m venv /opt/kitchentory/venv
sudo -u kitchentory /opt/kitchentory/venv/bin/pip install --upgrade pip
sudo -u kitchentory /opt/kitchentory/venv/bin/pip install -r requirements.txt
```

## Database Configuration

### 1. PostgreSQL Setup

```bash
# Initialize database (CentOS/RHEL only)
sudo postgresql-setup initdb

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE kitchentory;
CREATE USER kitchentory WITH PASSWORD 'secure_password_here';
ALTER ROLE kitchentory SET client_encoding TO 'utf8';
ALTER ROLE kitchentory SET default_transaction_isolation TO 'read committed';
ALTER ROLE kitchentory SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE kitchentory TO kitchentory;
\q
EOF
```

### 2. PostgreSQL Configuration

Edit `/etc/postgresql/13/main/postgresql.conf`:

```conf
# Memory settings
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

# Connection settings
max_connections = 100

# Write-ahead logging
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_min_duration_statement = 1000
```

Edit `/etc/postgresql/13/main/pg_hba.conf`:

```conf
# Add this line for application access
host    kitchentory     kitchentory     127.0.0.1/32           md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### 3. Redis Setup

```bash
# Start and enable Redis
sudo systemctl start redis
sudo systemctl enable redis

# Configure Redis security
sudo sed -i 's/^# requirepass.*/requirepass your_redis_password_here/' /etc/redis/redis.conf
sudo systemctl restart redis
```

## Application Deployment

### 1. Environment Configuration

Create `/opt/kitchentory/app/.env`:

```env
# Django settings
DEBUG=False
SECRET_KEY=your_very_long_secret_key_here
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DATABASE_URL=postgres://kitchentory:secure_password_here@localhost:5432/kitchentory

# Redis
REDIS_URL=redis://:your_redis_password_here@localhost:6379/0

# Email settings
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password

# Media files
MEDIA_ROOT=/opt/kitchentory/media
STATIC_ROOT=/opt/kitchentory/static

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
SECURE_CONTENT_TYPE_NOSNIFF=True
SECURE_BROWSER_XSS_FILTER=True
X_FRAME_OPTIONS=DENY

# Logging
LOG_LEVEL=INFO
LOG_DIR=/opt/kitchentory/logs

# External services
SENTRY_DSN=https://your_sentry_dsn_here
```

### 2. Create Required Directories

```bash
sudo -u kitchentory mkdir -p /opt/kitchentory/{media,static,logs}
```

### 3. Django Setup

```bash
cd /opt/kitchentory/app

# Set correct permissions
sudo chown -R kitchentory:kitchentory /opt/kitchentory/

# Run as kitchentory user
sudo -u kitchentory /opt/kitchentory/venv/bin/python manage.py collectstatic --noinput
sudo -u kitchentory /opt/kitchentory/venv/bin/python manage.py migrate
sudo -u kitchentory /opt/kitchentory/venv/bin/python manage.py createsuperuser
```

### 4. Gunicorn Configuration

Create `/opt/kitchentory/app/gunicorn.conf.py`:

```python
bind = "127.0.0.1:8000"
workers = 4
worker_class = "gevent"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 30
keepalive = 2

# Logging
accesslog = "/opt/kitchentory/logs/gunicorn-access.log"
errorlog = "/opt/kitchentory/logs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%({x-forwarded-for}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "kitchentory"

# Server mechanics
daemon = False
pidfile = "/opt/kitchentory/gunicorn.pid"
user = "kitchentory"
group = "kitchentory"
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

## Web Server Configuration

### 1. Nginx Configuration

Create `/etc/nginx/sites-available/kitchentory`:

```nginx
upstream kitchentory_server {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL configuration (will be added by Certbot)
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/x-javascript
        application/xml+rss
        application/javascript
        application/json;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;

    location = /favicon.ico {
        access_log off;
        log_not_found off;
    }

    location /static/ {
        alias /opt/kitchentory/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /opt/kitchentory/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    location /accounts/login/ {
        limit_req zone=login burst=5 nodelay;
        proxy_pass http://kitchentory_server;
        include proxy_params;
    }

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://kitchentory_server;
        include proxy_params;
    }

    location / {
        proxy_pass http://kitchentory_server;
        include proxy_params;
    }

    # Security
    location ~ /\.ht {
        deny all;
    }

    location ~ /\.(git|svn) {
        deny all;
    }
}
```

Create `/etc/nginx/proxy_params`:

```nginx
proxy_set_header Host $http_host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_redirect off;
proxy_buffering off;
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/kitchentory /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/TLS Setup

### 1. Install Certbot

```bash
# Ubuntu/Debian
sudo apt install certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 3. Auto-renewal Setup

```bash
sudo crontab -e
# Add this line:
0 12 * * * /usr/bin/certbot renew --quiet
```

## Monitoring and Logging

### 1. Supervisor Configuration

Create `/etc/supervisor/conf.d/kitchentory.conf`:

```ini
[program:kitchentory]
command=/opt/kitchentory/venv/bin/gunicorn kitchentory.wsgi:application -c /opt/kitchentory/app/gunicorn.conf.py
directory=/opt/kitchentory/app
user=kitchentory
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/kitchentory/logs/supervisor.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10

[program:kitchentory-celery]
command=/opt/kitchentory/venv/bin/celery -A kitchentory worker -l info
directory=/opt/kitchentory/app
user=kitchentory
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/kitchentory/logs/celery.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10

[program:kitchentory-beat]
command=/opt/kitchentory/venv/bin/celery -A kitchentory beat -l info
directory=/opt/kitchentory/app
user=kitchentory
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/kitchentory/logs/celery-beat.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
```

Start services:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

### 2. Log Rotation

Create `/etc/logrotate.d/kitchentory`:

```
/opt/kitchentory/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 kitchentory kitchentory
    postrotate
        supervisorctl restart kitchentory
    endscript
}
```

## Backup Strategy

### 1. Database Backup Script

Create `/opt/kitchentory/scripts/backup-db.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/kitchentory/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create database backup
pg_dump -h localhost -U kitchentory kitchentory | gzip > $BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete

echo "Database backup completed: $BACKUP_FILE"
```

### 2. Media Files Backup Script

Create `/opt/kitchentory/scripts/backup-media.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/opt/kitchentory/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/media_backup_$DATE.tar.gz"

# Create backup directory
mkdir -p $BACKUP_DIR

# Create media backup
tar -czf $BACKUP_FILE -C /opt/kitchentory media/

# Remove backups older than 7 days
find $BACKUP_DIR -name "media_backup_*.tar.gz" -mtime +7 -delete

echo "Media backup completed: $BACKUP_FILE"
```

### 3. Automated Backups

```bash
sudo crontab -e -u kitchentory
# Add these lines:
0 2 * * * /opt/kitchentory/scripts/backup-db.sh
0 3 * * * /opt/kitchentory/scripts/backup-media.sh
```

## Performance Optimization

### 1. Database Optimization

```sql
-- Connect to PostgreSQL as postgres user
sudo -u postgres psql kitchentory

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_inventory_item_household ON inventory_inventoryitem(household_id);
CREATE INDEX IF NOT EXISTS idx_inventory_item_product ON inventory_inventoryitem(product_id);
CREATE INDEX IF NOT EXISTS idx_inventory_item_location ON inventory_inventoryitem(location_id);
CREATE INDEX IF NOT EXISTS idx_inventory_item_expiration ON inventory_inventoryitem(expiration_date);
CREATE INDEX IF NOT EXISTS idx_recipe_created_by ON recipes_recipe(created_by_id);
CREATE INDEX IF NOT EXISTS idx_recipe_category ON recipes_recipe(category_id);
CREATE INDEX IF NOT EXISTS idx_shopping_list_household ON shopping_shoppinglist(household_id);
CREATE INDEX IF NOT EXISTS idx_shopping_item_list ON shopping_shoppinglistitem(shopping_list_id);

-- Analyze tables for query planner
ANALYZE;
```

### 2. Redis Configuration for Caching

Edit `/etc/redis/redis.conf`:

```conf
# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Performance
tcp-keepalive 300
timeout 0
```

### 3. Application-level Caching

Add to Django settings:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session engine
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## Security Hardening

### 1. Firewall Configuration

```bash
# Install UFW (Ubuntu) or firewalld (CentOS)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw deny 8000  # Block direct access to application server
```

### 2. Fail2Ban Setup

```bash
sudo apt install fail2ban  # Ubuntu
sudo yum install epel-release fail2ban  # CentOS

# Configure for Nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
```

Edit `/etc/fail2ban/jail.local`:

```ini
[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 5
bantime = 3600

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10
bantime = 600
```

### 3. System Hardening

```bash
# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Enable automatic security updates
sudo apt install unattended-upgrades  # Ubuntu

# Set up system limits
echo "kitchentory soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "kitchentory hard nofile 65536" | sudo tee -a /etc/security/limits.conf
```

## Maintenance

### 1. Health Check Script

Create `/opt/kitchentory/scripts/health-check.sh`:

```bash
#!/bin/bash

# Check application response
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/)
if [ $HTTP_STATUS -ne 200 ]; then
    echo "Application health check failed: HTTP $HTTP_STATUS"
    exit 1
fi

# Check database connection
sudo -u kitchentory /opt/kitchentory/venv/bin/python /opt/kitchentory/app/manage.py dbshell -c "SELECT 1;" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Database connection failed"
    exit 1
fi

# Check Redis connection
redis-cli -a your_redis_password_here ping > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Redis connection failed"
    exit 1
fi

echo "All health checks passed"
```

### 2. Update Script

Create `/opt/kitchentory/scripts/update.sh`:

```bash
#!/bin/bash

cd /opt/kitchentory/app

# Pull latest code
sudo -u kitchentory git pull origin main

# Update dependencies
sudo -u kitchentory /opt/kitchentory/venv/bin/pip install -r requirements.txt

# Run migrations
sudo -u kitchentory /opt/kitchentory/venv/bin/python manage.py migrate

# Collect static files
sudo -u kitchentory /opt/kitchentory/venv/bin/python manage.py collectstatic --noinput

# Restart services
sudo supervisorctl restart kitchentory
sudo supervisorctl restart kitchentory-celery
sudo supervisorctl restart kitchentory-beat

echo "Update completed successfully"
```

### 3. Monitoring Commands

```bash
# Check application status
sudo supervisorctl status

# View application logs
tail -f /opt/kitchentory/logs/gunicorn-error.log

# Check database performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname = 'kitchentory';"

# Monitor system resources
htop
iostat -x 1
```

## Troubleshooting

### Common Issues

#### 1. Application Won't Start

```bash
# Check supervisor logs
sudo tail -f /var/log/supervisor/supervisord.log

# Check gunicorn logs
sudo tail -f /opt/kitchentory/logs/gunicorn-error.log

# Test configuration
sudo -u kitchentory /opt/kitchentory/venv/bin/python /opt/kitchentory/app/manage.py check
```

#### 2. Database Connection Issues

```bash
# Test database connection
sudo -u postgres psql -c "\l" | grep kitchentory

# Check PostgreSQL status
sudo systemctl status postgresql

# View PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

#### 3. SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Test SSL configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Renew certificate manually
sudo certbot renew --dry-run
```

#### 4. Performance Issues

```bash
# Check system resources
free -h
df -h
top

# Check database slow queries
sudo -u postgres psql kitchentory -c "SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# Check Nginx access patterns
sudo tail -f /var/log/nginx/access.log | grep "POST\|PUT\|DELETE"
```

### Emergency Procedures

#### 1. Database Recovery

```bash
# Stop application
sudo supervisorctl stop kitchentory

# Restore from backup
sudo -u postgres dropdb kitchentory
sudo -u postgres createdb kitchentory
gunzip -c /opt/kitchentory/backups/db_backup_YYYYMMDD_HHMMSS.sql.gz | sudo -u postgres psql kitchentory

# Start application
sudo supervisorctl start kitchentory
```

#### 2. Rollback Deployment

```bash
cd /opt/kitchentory/app

# Revert to previous version
sudo -u kitchentory git log --oneline -5  # Find previous commit
sudo -u kitchentory git reset --hard COMMIT_HASH

# Restart services
sudo supervisorctl restart all
```

## Load Balancer Setup (Optional)

For high-availability deployments, use a load balancer:

### HAProxy Configuration

```haproxy
global
    daemon
    user haproxy
    group haproxy

defaults
    mode http
    timeout connect 5000ms
    timeout client 50000ms
    timeout server 50000ms

frontend kitchentory_frontend
    bind *:80
    bind *:443 ssl crt /etc/ssl/certs/kitchentory.pem
    redirect scheme https if !{ ssl_fc }
    default_backend kitchentory_backend

backend kitchentory_backend
    balance roundrobin
    server app1 10.0.1.10:8000 check
    server app2 10.0.1.11:8000 check
```

## Container Deployment (Alternative)

### Docker Compose for Production

```yaml
version: '3.8'

services:
  web:
    image: kitchentory:latest
    restart: unless-stopped
    environment:
      - DATABASE_URL=postgres://kitchentory:password@db:5432/kitchentory
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - media_data:/app/media
      - static_data:/app/static

  db:
    image: postgres:13
    restart: unless-stopped
    environment:
      - POSTGRES_DB=kitchentory
      - POSTGRES_USER=kitchentory
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6
    restart: unless-stopped
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_data:/app/static
      - media_data:/app/media

volumes:
  postgres_data:
  redis_data:
  media_data:
  static_data:
```

This deployment guide provides a comprehensive foundation for running Kitchentory in production. Always test thoroughly in a staging environment before deploying to production.