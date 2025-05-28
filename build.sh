#!/bin/bash

# Exit on error
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Apply database migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --no-input

# Create superuser if needed (will be skipped if user exists)
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true
