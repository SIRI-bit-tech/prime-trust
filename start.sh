#!/usr/bin/env bash
set -o errexit

# Run database migrations
echo "Running migrations..."
python3 manage.py migrate --no-input

# Create superuser if not exists (requires DJANGO_SUPERUSER_* env vars)
echo "Creating superuser..."
python3 manage.py createsuperuser \
    --no-input \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "$DJANGO_SUPERUSER_EMAIL" \
    --first_name "$DJANGO_SUPERUSER_FIRST_NAME" \
    --last_name "$DJANGO_SUPERUSER_LAST_NAME" || true

echo "Starting Gunicorn server..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 4 \
    --timeout 120 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=-