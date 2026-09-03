FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install shared requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared backend models/core and worker tasks
COPY backend/ ./backend/
COPY worker/ ./worker/

# Ensure backend and worker are discoverable on PYTHONPATH
ENV PYTHONPATH=/app/backend:/app

CMD ["celery", "-A", "worker.celery_app", "worker", "-Q", "high,default,low", "--loglevel=info"]
