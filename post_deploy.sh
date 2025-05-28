#!/bin/bash

# Exit on error
set -o errexit

# Apply database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input

# Create default superuser (will be skipped if user exists)
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

# Run any additional post-deployment tasks
echo "Running post-deployment tasks..."

# Set up initial site in the database for sitemap
python manage.py shell -c "from django.contrib.sites.models import Site; Site.objects.update_or_create(id=1, defaults={'domain': 'primetrust.yourdomain.com', 'name': 'PrimeTrust'})"
