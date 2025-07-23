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

# Run migrations, create subscription plans, and start server
CMD python manage.py migrate && \
    python manage.py create_subscription_plans && \
    gunicorn kitchentory.wsgi:application --bind 0.0.0.0:$PORT