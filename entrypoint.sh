#!/bin/sh
set -e

echo "Running database migrations..."
flask --app main db upgrade

echo "Starting server..."
exec python -m gunicorn --bind 0.0.0.0:8000 --workers 3 main:app
