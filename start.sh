#!/bin/bash

# Exit on error
set -o errexit

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input

# Create superuser if it doesn't exist
echo "Ensuring default superuser exists..."
python manage.py shell -c "\
from django.contrib.auth import get_user_model; \
User = get_user_model(); \
User.objects.filter(username='admin').exists() or \
User.objects.create_superuser('admin', 'admin@example.com', 'changeme')"

# Ensure the default site is configured
echo "Configuring default site..."
python manage.py shell -c "\
from django.contrib.sites.models import Site; \
Site.objects.update_or_create(id=1, defaults={'domain': 'primetrust.yourdomain.com', 'name': 'PrimeTrust'})"

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 4 \
    --timeout 120 \
    --log-level=info
