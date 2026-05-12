#!/bin/bash
set -e

echo "🚀 Starting Superset Initialization..."

# 1. Wait for Postgres to be ready
echo "Waiting for PostgreSQL at postgres:5432..."
until nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL is up!"

# 2. Database upgrade (Migrations)
echo "Running database migrations..."
superset db upgrade

# 3. Create Admin user if not exists
echo "Checking for admin user..."
superset fab create-admin \
    --username admin \
    --firstname Admin \
    --lastname User \
    --email admin@local.com \
    --password admin || echo "Admin user already exists."

# 4. Initialize Superset (Roles, Permissions)
echo "Initializing roles and permissions..."
superset init

# 5. Run the Custom Import Wizard
echo "Running Custom Import Wizard..."
python /app/import_wizard.py


# 6. Start the production server
echo "Starting Superset with Gunicorn..."
gunicorn \
    --bind  "0.0.0.0:8088" \
    --workers 4 \
    --worker-class gthread \
    --threads 4 \
    --timeout 60 \
    --limit-request-line 0 \
    --limit-request-field_size 0 \
    "superset.app:create_app()"
