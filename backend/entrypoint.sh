#!/bin/sh
set -e

echo "Applying Alembic database migrations..."
alembic upgrade head

echo "Starting FlowForge FastAPI backend server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
