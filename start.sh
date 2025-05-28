#!/bin/bash
set -o errexit

echo "Starting Gunicorn server..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 4 \
    --timeout 120 \
    --log-level=info \
    --access-logfile=- \
    --error-logfile=-