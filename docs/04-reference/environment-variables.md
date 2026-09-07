# Environment Variables & Configuration Specification

FlowForge utilizes a centralized, type-safe configuration system driven by Pydantic Settings (`pydantic-settings`) in Python and Next.js environment resolution in TypeScript. This document provides an exhaustive reference of all environment variables, precedence rules, schema validation constraints, security mandates, and production deployment templates.

---

## Configuration Architecture & Resolution Pipeline

FlowForge services resolve configuration using a tiered precedence model where operating system environment variables (such as Docker container environment injections or Kubernetes ConfigMaps/Secrets) take highest priority over local `.env` files and fallback defaults.

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'darkMode': true,
    'background': '#0b0f19',
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#94a3b8'
  }
}}%%
flowchart TD
    subgraph Sources ["Configuration Ingestion Tier"]
        ENV["Host OS / Shell / Container Environment<br/><code>export VAR=value</code> (Highest Precedence)"]
        BE_ENV["Backend Local File<br/><code>backend/.env</code>"]
        ROOT_ENV["Repository Root File<br/><code>.env</code>"]
        DEFAULTS["Pydantic Settings Defaults<br/><code>backend/app/core/config.py</code> (Lowest Precedence)"]
    end

    subgraph Parser ["Resolution & Validation Engine"]
        SETTINGS["Pydantic BaseSettings<br/><code>SettingsConfigDict(extra='ignore')</code>"]
        SQLITE_VAL["Validator: <code>resolve_sqlite_path</code><br/>Resolves relative SQLite paths"]
        CORS_VAL["Validator: <code>assemble_cors_origins</code><br/>Parses JSON arrays & CSV strings"]
    end

    subgraph Consumers ["Target Runtime Consumers"]
        FASTAPI["FastAPI Backend (Port 8000)<br/>Auth, DB Session, CORS"]
        WORKER["Celery Worker Cluster<br/>Redis Broker, DB Tasks, Retry Engine"]
        FRONTEND["Next.js Frontend (Port 3000)<br/><code>NEXT_PUBLIC_API_URL</code> (Client / Server)"]
        CONTAINERS["PostgreSQL (5432) & Redis (6379)<br/>Container Initialization"]
    end

    ENV --> SETTINGS
    BE_ENV --> SETTINGS
    ROOT_ENV --> SETTINGS
    DEFAULTS --> SETTINGS

    SETTINGS --> SQLITE_VAL
    SETTINGS --> CORS_VAL

    SQLITE_VAL --> FASTAPI
    SQLITE_VAL --> WORKER
    CORS_VAL --> FASTAPI
    SETTINGS --> FASTAPI
    SETTINGS --> WORKER
    ENV -.-> FRONTEND
    ENV -.-> CONTAINERS

    classDef source fill:#0f172a,stroke:#38bdf8,stroke-width:1px,color:#f8fafc;
    classDef engine fill:#1e1b4b,stroke:#818cf8,stroke-width:1px,color:#f8fafc;
    classDef consumer fill:#0f172a,stroke:#34d399,stroke-width:1px,color:#f8fafc;
    class ENV,BE_ENV,ROOT_ENV,DEFAULTS source;
    class SETTINGS,SQLITE_VAL,CORS_VAL engine;
    class FASTAPI,WORKER,FRONTEND,CONTAINERS consumer;
```

---

## Configuration Precedence Order

When initializing the backend or Celery worker, Pydantic Settings evaluates configuration in the following order (first match wins):

1. **Host Environment Variables**: Injected via container runtime (`docker compose`, Kubernetes pod specs, or system shell `export`).
2. **`backend/.env`**: Local environment file in the backend directory.
3. **`PROJECT_ROOT/.env`**: Top-level `.env` file in the repository root.
4. **Current Working Directory `.env`**: Relative `.env` path from process execution directory.
5. **Parent Directory `../.env`**: Relative parent search.
6. **Hardcoded Schema Defaults**: Defined on fields in [backend/app/core/config.py](file:///d:/Edutation%28P%29/FlowForge/backend/app/core/config.py).

> [!IMPORTANT]
> Next.js inlines variables prefixed with `NEXT_PUBLIC_` into browser JavaScript bundles at **build time** (`npm run build`). When deploying pre-built Docker containers, ensure `NEXT_PUBLIC_API_URL` is set correctly during `docker build` via `--build-arg` if the browser client connects to a custom domain.

---

## Master Environment Variables Matrix

### 1. Database & Persistence Layer

Configures PostgreSQL connection parameters and SQLAlchemy database engine pooling.
- **Reference**: [backend/app/core/db.py](file:///d:/Edutation%28P%29/FlowForge/backend/app/core/db.py), [backend/app/core/config.py](file:///d:/Edutation%28P%29/FlowForge/backend/app/core/config.py)

| Variable Name | Target Services | Type | Default Value | Example Values | Description & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`DATABASE_URL`** | `backend`, `worker` | `string` | `postgresql://postgres:postgres@localhost:5432/flowforge` | `postgresql://user:pass@postgres:5432/flowforge`<br/>`sqlite:///test.db` | Full SQLAlchemy database connection URI. Inside Docker Compose, host is `postgres`. Relative SQLite paths are automatically resolved against `backend/`. |
| **`POSTGRES_USER`** | `postgres`, `docker-compose` | `string` | `postgres` | `flowforge_admin` | Superuser username for PostgreSQL container initialization and health checks. |
| **`POSTGRES_PASSWORD`** | `postgres`, `docker-compose` | `string` | `postgres` | `sUp3r-S3cur3-P@ssw0rd!` | Authentication password for PostgreSQL superuser. Must be changed in production. |
| **`POSTGRES_DB`** | `postgres`, `docker-compose` | `string` | `flowforge` | `flowforge_prod` | Default database catalog created upon initial PostgreSQL container provisioning. |

---

### 2. Message Broker & Queue Transport

Configures Celery distributed task queuing and Redis state storage.
- **Reference**: [worker/celery_app.py](file:///d:/Edutation%28P%29/FlowForge/worker/celery_app.py), [backend/app/core/config.py](file:///d:/Edutation%28P%29/FlowForge/backend/app/core/config.py)

| Variable Name | Target Services | Type | Default Value | Example Values | Description & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`REDIS_URL`** | `backend`, `worker`, `docker-compose` | `string` | `redis://localhost:6379/0` | `redis://redis:6379/0`<br/>`rediss://:auth@redis.cloud:6380/0` | Primary Redis connection URI used as both Celery AMQP-compatible broker and task result backend. Host is `redis` in Docker; `localhost` native. Supports SSL via `rediss://`. |
| **`CELERY_BROKER_URL`** | `worker`, `backend` *(Optional)* | `string` | Value of `REDIS_URL` | `redis://localhost:6379/0` | Optional legacy alias for Celery broker URI. In FlowForge, `worker/celery_app.py` resolves `settings.REDIS_URL` directly. |
| **`CELERY_RESULT_BACKEND`** | `worker`, `backend` *(Optional)* | `string` | Value of `REDIS_URL` | `redis://localhost:6379/0` | Optional legacy alias for Celery task result backend storage. |

---

### 3. Security, Authentication & Networking

Controls cryptographic signing, token lifespans, and Cross-Origin Resource Sharing boundaries.
- **Reference**: [backend/app/core/security.py](file:///d:/Edutation%28P%29/FlowForge/backend/app/core/security.py), [backend/app/api/auth.py](file:///d:/Edutation%28P%29/FlowForge/backend/app/api/auth.py)

| Variable Name | Target Services | Type | Default Value | Example Values | Description & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`JWT_SECRET`** | `backend`, `worker` | `string` | `flowforge_default_secret_key_change_in_production` | `f8a4e3... (64-byte hex)` | Cryptographic secret key used to sign and verify HMAC-SHA256 JWT access and refresh tokens. **Mandatory to replace in production environments.** |
| **`JWT_EXPIRE_MINUTES`**| `backend` | `integer` | `60` | `15`, `120`, `1440` | Lifetime duration in minutes for access tokens issued via `/auth/login` and `/auth/register`. |
| **`CORS_ORIGINS`** | `backend` | `list[str]` or `string` | `["http://localhost:3000"]` | `http://localhost:3000,https://app.flowforge.io`<br/>`["https://flowforge.io"]` | Allowed HTTP origins for browser CORS preflight. Parsed flexibly from JSON arrays or comma-separated strings via Pydantic validator. |

---

### 4. Pipeline Resilience & Exponential Backoff

Governs automated retry timing schedules and dead-letter quarantine thresholds for failed tasks.
- **Reference**: [worker/tasks/execute_task.py](file:///d:/Edutation%28P%29/FlowForge/worker/tasks/execute_task.py)

| Variable Name | Target Services | Type | Default Value | Example Values | Description & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`RETRY_BASE_DELAY_SECONDS`** | `worker`, `backend` | `float` | `10.0` | `5.0`, `15.0` | Base multiplier in seconds for exponential backoff calculations: $\text{delay} = \text{base} \times 2^{\text{attempt}-1}$. |
| **`RETRY_MAX_DELAY_SECONDS`** | `worker`, `backend` | `float` | `300.0` | `60.0`, `600.0` | Absolute ceiling cap in seconds preventing exponential backoff delays from growing indefinitely on persistent failures. |

---

### 5. Frontend & Client Application

Governs Next.js browser client routing and backend communication.
- **Reference**: [frontend/src/lib/api.ts](file:///d:/Edutation%28P%29/FlowForge/frontend/src/lib/api.ts), [frontend/Dockerfile](file:///d:/Edutation%28P%29/FlowForge/frontend/Dockerfile)

| Variable Name | Target Services | Type | Default Value | Example Values | Description & Constraints |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`NEXT_PUBLIC_API_URL`** | `frontend` | `string` | `http://localhost:8000` | `http://localhost:8000`<br/>`https://api.flowforge.yourdomain.com` | Public base URL of the FastAPI backend reachable from the user's browser. Exposed to client-side code via Next.js `NEXT_PUBLIC_` convention. |
| **`NODE_ENV`** | `frontend` | `string` | `development` | `production`, `test` | Node runtime execution mode. Set to `production` in containerized builds to trigger Next.js optimizations. |
| **`PORT`** | `frontend` | `integer` | `3000` | `3000`, `80` | Internal network port bound by Next.js HTTP server. |

---

## Runtime Type Validation & Field Validators

FlowForge utilizes custom Pydantic validators in [backend/app/core/config.py](file:///d:/Edutation%28P%29/FlowForge/backend/app/core/config.py) to prevent configuration drift and facilitate seamless cross-platform execution:

### 1. Relative SQLite Path Resolution (`resolve_sqlite_path`)
To ensure integration tests and lightweight local runs work across operating systems regardless of the current working directory, relative SQLite URLs are automatically converted to absolute paths relative to `backend/`:
```python
@field_validator("DATABASE_URL", mode="before")
@classmethod
def resolve_sqlite_path(cls, v: str) -> str:
    if (
        isinstance(v, str)
        and v.startswith("sqlite:///")
        and not v.startswith("sqlite:////")
        and not v.startswith("sqlite:///:memory:")
    ):
        rel_path = v.replace("sqlite:///", "")
        if rel_path.startswith("./"):
            rel_path = rel_path[2:]
        abs_path = (BACKEND_DIR / rel_path).resolve()
        return f"sqlite:///{abs_path.as_posix()}"
    return v
```

### 2. Dual-Format CORS Parsing (`assemble_cors_origins`)
Allows operators to configure `CORS_ORIGINS` as either a native JSON array or a simple comma-separated string:
```python
@field_validator("CORS_ORIGINS", mode="before")
@classmethod
def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
    if isinstance(v, str):
        v_stripped = v.strip()
        if v_stripped.startswith("[") and v_stripped.endswith("]"):
            try:
                return json.loads(v_stripped)
            except Exception:
                pass
        return [origin.strip() for origin in v.split(",") if origin.strip()]
    return v
```

---

## Environment Profiles & Ready-to-Use Templates

### Profile 1: Full-Stack Docker Compose (`infrastructure/.env`)
Use this template when orchestrating the platform via `docker compose -f infrastructure/docker-compose.yml up`:

```bash
# ==============================================================================
# FlowForge Docker Compose Environment Configuration
# Save as: infrastructure/.env
# ==============================================================================

# PostgreSQL Container Provisioning
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=flowforge

# Inter-Container Networking URIs (Internal Bridge Network: flowforge_network)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/flowforge
REDIS_URL=redis://redis:6379/0

# Security & Authentication
JWT_SECRET=flowforge_super_secret_jwt_key_change_in_production
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000

# Pipeline Resilience
RETRY_BASE_DELAY_SECONDS=10.0
RETRY_MAX_DELAY_SECONDS=300.0

# Frontend Browser Client
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### Profile 2: Local Native Development (`backend/.env` & `frontend/.env.local`)
Use these templates when running services natively on the host OS without Docker:

#### Backend & Celery Worker (`backend/.env` or repository root `.env`):
```bash
# ==============================================================================
# FlowForge Local Development Environment
# Save as: backend/.env or .env
# ==============================================================================

# Host-Accessible Service Endpoints
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/flowforge
REDIS_URL=redis://localhost:6379/0

# Optional Celery Aliases
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security Settings
JWT_SECRET=local_dev_jwt_secret_not_for_production_use
JWT_EXPIRE_MINUTES=120
CORS_ORIGINS=http://localhost:3000

# Retry Parameters
RETRY_BASE_DELAY_SECONDS=5.0
RETRY_MAX_DELAY_SECONDS=60.0
```

#### Frontend Dashboard (`frontend/.env.local`):
```bash
# ==============================================================================
# Next.js Local Client Configuration
# Save as: frontend/.env.local
# ==============================================================================

NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### Profile 3: Hardened Production Deployment
Use this template when deploying to production environments (AWS ECS, Kubernetes, Google Cloud Run, DigitalOcean App Platform):

```bash
# ==============================================================================
# FlowForge Hardened Production Configuration
# Inject via: Kubernetes Secret / AWS Secrets Manager / Vault
# ==============================================================================

# Managed PostgreSQL (e.g., AWS RDS, Cloud SQL) with SSL
DATABASE_URL=postgresql://flowforge_app:k9$mQ2!vL9zP@prod-db.internal.flowforge.io:5432/flowforge_prod?sslmode=require

# Managed Redis Cluster (e.g., AWS ElastiCache) with TLS and Auth
REDIS_URL=rediss://:ComplexRedisAuthToken123@prod-redis.internal.flowforge.io:6379/0

# High-Entropy Cryptographic Secret (Generated via openssl rand -hex 32)
JWT_SECRET=4d9e18b8f2c37e90a5d46e1c2b87f9018e5a7d6c3b2e1f0a9d8c7b6e5f4a3b2c
JWT_EXPIRE_MINUTES=30

# Strict CORS Allowlist (No Wildcards)
CORS_ORIGINS=https://app.flowforge.io,https://admin.flowforge.io

# Production Retry Policy
RETRY_BASE_DELAY_SECONDS=10.0
RETRY_MAX_DELAY_SECONDS=300.0

# Production Browser API Endpoint
NEXT_PUBLIC_API_URL=https://api.flowforge.io
```

---

## Security Governance & Best Practices

> [!CAUTION]
> Running FlowForge in production with default secrets (`flowforge_default_secret_key_change_in_production`) allows unauthorized attackers to forge valid administrative JWT tokens and compromise workflow execution.

1. **Secret Generation**:
   Always generate production secrets using cryptographically secure pseudorandom number generators:
   ```bash
   # Generate a 256-bit (64-character hex) JWT secret
   openssl rand -hex 32

   # Alternative via Python standard library
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. **Secret Rotation Strategy**:
   - Update `JWT_SECRET` during a maintenance window or implement dual-key validation.
   - When rotated, all active access and refresh tokens are immediately invalidated, requiring users to log in again.

3. **CORS Restrictions**:
   - Never set `CORS_ORIGINS=*` in production environments.
   - Restrict origins explicitly to the domain hosting the frontend dashboard.

4. **Version Control Sanitation**:
   - Ensure `.env`, `.env.local`, and `infrastructure/.env` are listed in `.gitignore`.
   - Never commit actual passwords, secrets, or connection strings to git repositories.
   - Only commit `.env.example` templates containing sanitized placeholder values.

---

## Diagnostic Matrix: Configuration Troubleshooting

| Symptom / Error Message | Root Cause | Remediation Procedure |
| :--- | :--- | :--- |
| `pydantic_core._pydantic_core.ValidationError: Input should be a valid integer` | Non-numeric value supplied for `JWT_EXPIRE_MINUTES` or retry delays. | Ensure integer/float values contain only valid digits without quotes or units (e.g., `JWT_EXPIRE_MINUTES=60`, not `60m`). |
| `sqlalchemy.exc.OperationalError: could not connect to server: Connection refused` | `DATABASE_URL` is pointing to `localhost` inside Docker or database is offline. | Inside Docker Compose, set host to `postgres` (`postgresql://.../@postgres:5432/...`). Ensure `postgres` container passes healthcheck. |
| `redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379` | Worker or backend cannot reach Redis instance. | Inside Docker Compose, set `REDIS_URL=redis://redis:6379/0`. On local development, start Redis on port `6379`. |
| `Access to fetch at ... has been blocked by CORS policy` | Origin header of frontend is not included in `CORS_ORIGINS`. | Add frontend URL (e.g., `http://localhost:3000`) to `CORS_ORIGINS` in `backend/.env` or Docker environment. |
| Frontend displays blank cards or network errors in browser | `NEXT_PUBLIC_API_URL` is pointing to container hostname (`http://backend:8000`) instead of browser-routable URL. | Because the browser executes client-side code on the user's computer, `NEXT_PUBLIC_API_URL` must point to host port `http://localhost:8000` or public domain. |

---

## Related Documentation & References

- [REST API Reference](api-reference.md) — Endpoint contracts, authentication headers, and status codes.
- [Relational Data Model & Architecture](data-model.md) — Database schema, ORM mappings, and cascade constraints.
- [Running Locally Without Docker](../03-how-to-guides/running-locally-without-docker.md) — Host environment setup and native process management.
- [Docker Architecture & Orchestration](../02-tutorials/understanding-docker.md) — Container network bridge and volume configurations.
- [Deploying to Production](../03-how-to-guides/deploying-to-production.md) — Cloud infrastructure provisioning and secrets management.