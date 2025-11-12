#!/bin/sh
set -e

echo "Executing migrations..."
python manage.py migrate --noinput

exec "$@"

