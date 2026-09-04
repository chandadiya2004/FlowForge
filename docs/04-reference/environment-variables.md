# Environment Variables

This document provides a comprehensive reference of all environment variables used across FlowForge services, including the FastAPI backend, Celery worker, Next.js frontend, PostgreSQL database, and Docker Compose configurations.

---

## Complete Variables Reference

### 1. Database Configuration (PostgreSQL & SQLAlchemy)

| Variable | Used By | Description | Example Value | Required (Default) |
| :--- | :--- | :--- | :--- | :--- |
| `DATABASE_URL` | backend, worker | Complete SQLAlchemy connection string. Inside Docker, host is `postgres`; on native host development, host is `localhost`. Supports SQLite paths for testing. | `postgresql://postgres:postgres@postgres:5432/flowforge` | No (Defaults to `postgresql://postgres:postgres@localhost:5432/flowforge`) |
| `POSTGRES_USER` | postgres, docker-compose | Database superuser account created on initial container initialization. | `postgres` | No (Defaults to `postgres`) |
| `POSTGRES_PASSWORD` | postgres, docker-compose | Password for the PostgreSQL superuser. | `postgres` | No (Defaults to `postgres`) |
| `POSTGRES_DB` | postgres, docker-compose | Default database name created on container initialization. | `flowforge` | No (Defaults to `flowforge`) |

---

### 2. Broker & Queue Configuration (Redis & Celery)

| Variable | Used By | Description | Example Value | Required (Default) |
| :--- | :--- | :--- | :--- | :--- |
| `REDIS_URL` | backend, worker, docker-compose | Redis connection URI used by Celery for message queue transport and task state tracking. Host is `redis` in Docker; `localhost` on host. | `redis://redis:6379/0` | No (Defaults to `redis://localhost:6379/0`) |
| `CELERY_BROKER_URL` | worker, backend *(local template)* | Optional alias for the Celery message broker URI. If unset, FlowForge reads `REDIS_URL`. | `redis://localhost:6379/0` | No (Defaults to `REDIS_URL`) |
| `CELERY_RESULT_BACKEND` | worker, backend *(local template)* | Optional alias for Celery task result storage URI. If unset, FlowForge reads `REDIS_URL`. | `redis://localhost:6379/0` | No (Defaults to `REDIS_URL`) |

---

### 3. Security & Authentication (JWT & Passlib)

| Variable | Used By | Description | Example Value | Required (Default) |
| :--- | :--- | :--- | :--- | :--- |
| `JWT_SECRET` | backend, worker | Cryptographic secret key used to sign and verify HMAC-SHA256 JWT access and refresh tokens. Must be changed to a high-entropy string in production. | `flowforge_super_secret_jwt_key_change_in_production` | No (Defaults to `flowforge_default_secret_key_change_in_production`) |
| `JWT_EXPIRE_MINUTES` | backend | Access token validity duration in minutes. After expiration, clients must use `/auth/refresh` to acquire a new token. | `60` | No (Defaults to `60`) |
| `CORS_ORIGINS` | backend | Allowed origins for Cross-Origin Resource Sharing. Can be formatted as a JSON array (`["http://localhost:3000"]`) or comma-separated string. | `http://localhost:3000` | No (Defaults to `["http://localhost:3000"]`) |

---

### 4. Retry & Exponential Backoff Configuration

| Variable | Used By | Description | Example Value | Required (Default) |
| :--- | :--- | :--- | :--- | :--- |
| `RETRY_BASE_DELAY_SECONDS` | worker, backend | Base delay in seconds used to calculate exponential backoff on task failures ($\text{delay} = \text{base} \times 2^{\text{attempt}-1}$). | `10.0` | No (Defaults to `10.0`) |
| `RETRY_MAX_DELAY_SECONDS` | worker, backend | Maximum upper bound (cap) for exponential backoff delay, preventing retry intervals from expanding indefinitely. | `300.0` | No (Defaults to `300.0`) |

---

### 5. Frontend Dashboard Configuration

| Variable | Used By | Description | Example Value | Required (Default) |
| :--- | :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | frontend, docker-compose | Base URL of the FastAPI backend reachable from the user's browser. Used by the frontend HTTP client. | `http://localhost:8000` | No (Defaults to `http://localhost:8000`) |

---

## Configuration File Locations

FlowForge reads environment variables according to service context:

1. **Docker Compose Stack**: Loaded from `infrastructure/.env` (or inherited from host shell environment).
2. **Backend (Local Host)**: `backend/.env` (parsed via `pydantic-settings` in `backend/app/core/config.py`).
3. **Frontend (Local Host)**: `frontend/.env.local` (parsed natively by Next.js).