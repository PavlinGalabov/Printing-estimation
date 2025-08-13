#!/usr/bin/env bash
# exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Load initial data (your existing database data)
python manage.py loaddata fixtures/initial_data.json

# Collect static files
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist (optional)
echo "Build script completed successfully!"