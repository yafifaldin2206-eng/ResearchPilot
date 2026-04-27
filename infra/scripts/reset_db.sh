#!/bin/bash
# Drop and recreate the database, re-run migrations from scratch.
# WARNING: this deletes all data.
# Usage: bash infra/scripts/reset_db.sh

set -e

echo "This will DELETE all data. Continue? (y/N)"
read -r confirm
if [[ "$confirm" != "y" ]]; then
  echo "Aborted."
  exit 0
fi

echo "Dropping and recreating database..."
docker-compose exec postgres psql -U researchpilot -c "DROP DATABASE IF EXISTS researchpilot;"
docker-compose exec postgres psql -U researchpilot -c "CREATE DATABASE researchpilot;"

echo "Running migrations..."
docker-compose exec backend alembic upgrade head

echo "Seeding companies..."
docker-compose exec backend python /app/../infra/scripts/seed_companies.py

echo "Done."
