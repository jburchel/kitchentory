FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Install npm dependencies and build CSS
RUN npm install && npm run build-css

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations, create subscription plans, create temp admin, and start server
CMD python manage.py migrate && \
    python manage.py create_subscription_plans && \
    python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
if not User.objects.filter(email='temp@admin.com').exists():
    User.objects.create_user(email='temp@admin.com', password='TempAdmin123!', is_staff=True, is_superuser=True, is_active=True);
    print('Temp admin created: temp@admin.com / TempAdmin123!')
" && \
    gunicorn kitchentory.wsgi:application --bind 0.0.0.0:$PORT