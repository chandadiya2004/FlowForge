# How to Run FlowForge Locally in Hybrid Mode (Without Full Docker)

While Docker Compose is the recommended way to run FlowForge in production and CI, rebuilding container images on every code edit can slow down day-to-day feature development. 

This guide details the **hybrid development workflow**: running PostgreSQL and Redis in lightweight, persistent Docker containers while running the FastAPI backend, Celery worker, and Next.js frontend directly on your host machine with sub-second hot-reloading and native IDE debugging.

---

## Hybrid Architecture Topology

In hybrid mode, your host operating system runs the application code directly, communicating with containerized infrastructure through published `localhost` ports:

```mermaid
%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'darkMode': true,
    'background': '#0b0f19',
    'mainBkg': '#0f172a',
    'primaryColor': '#1e293b',
    'primaryTextColor': '#f8fafc',
    'primaryBorderColor': '#38bdf8',
    'lineColor': '#94a3b8',
    'secondaryColor': '#0f172a',
    'tertiaryColor': '#1e293b'
  }
}}%%
flowchart TB
    classDef host fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;
    classDef container fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#faf5ff;
    classDef broker fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fef2f2;
    classDef client fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;

    subgraph HostProcesses ["Host Machine Process Space (Instant Hot-Reloading)"]
        Browser["Host Web Browser\n(http://localhost:3000)"]:::client
        FrontendDev["Terminal 3: Next.js Dev Server\n(npm run dev :3000)\nFast Refresh on Edit"]:::host
        BackendDev["Terminal 1: FastAPI Uvicorn\n(uvicorn main:app --reload :8000)\nAuto-Reload on Save"]:::host
        WorkerDev["Terminal 2: Celery Worker\n(celery -A celery_app ...)\nDirect Python Tracebacks"]:::host
    end

    subgraph DockerBridge ["Docker Bridge Space (Minimal Infrastructure Only)"]
        PostgresContainer[("flowforge-postgres (:5432)\nPostgreSQL 16\nNamed Volume: postgres_data")]:::container
        RedisContainer[("flowforge-redis (:6379)\nRedis 7 Broker\nQueues: high, default, low")]:::broker
    end

    %% Web UI Interactions
    Browser -->|"HTTP :3000 (UI Rendering)"| FrontendDev
    Browser -->|"HTTP REST :8000 (API Requests)"| BackendDev

    %% Host to Container Connections via localhost
    FrontendDev -->|"HTTP API Calls"| BackendDev
    BackendDev -->|"TCP localhost:5432 (SQLAlchemy)"| PostgresContainer
    BackendDev -->|"TCP localhost:6379 (redis-py)"| RedisContainer
    WorkerDev -->|"TCP localhost:6379 (BRPOP Tasks)"| RedisContainer
    WorkerDev -->|"TCP localhost:5432 (State Writes)"| PostgresContainer

    style HostProcesses fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f0f9ff
    style DockerBridge fill:#0b0f19,stroke:#c084fc,stroke-width:1.5px,stroke-dasharray: 6 6,color:#faf5ff
```

### Component Responsibility Breakdown

| Component | Execution Context | Operational Benefit |
| :--- | :--- | :--- |
| **PostgreSQL 16** | Docker Container (`localhost:5432`) | Eliminates manual database engine installation, user creation, and service management. |
| **Redis 7** | Docker Container (`localhost:6379`) | Provides in-memory priority queue broker with persistent disk snapshots. |
| **FastAPI Backend** | Host Machine (`localhost:8000`) | Uvicorn hot-reloads (`--reload`) instantly whenever Python files in `backend/app/` are saved. |
| **Celery Worker** | Host Machine (Background Process) | Enables interactive breakpoints (`pdb`), immediate stack traces, and rapid handler iteration. |
| **Next.js Frontend** | Host Machine (`localhost:3000`) | Next.js Fast Refresh applies TypeScript and Tailwind CSS updates in milliseconds without full page reloads. |

---

## Prerequisites

Ensure the following runtimes are installed on your host machine:

- **Docker Desktop** (Engine 24+, Compose v2) — to host PostgreSQL and Redis.
- **Python 3.11+** — to run the backend and worker environments.
- **Node.js 20+ LTS** & **npm 10+** — to run the frontend development server.

---

## Step 1: Launch PostgreSQL and Redis via Docker Compose

Spin up **only** the data tier services using Docker Compose:

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
```

Confirm that both services have passed their health check probes:

```bash
docker compose -f infrastructure/docker-compose.yml ps
```

**Expected Status Output:**
```text
NAME                 IMAGE                COMMAND                  SERVICE    STATUS
flowforge-postgres   postgres:16-alpine   "docker-entrypoint.s…"   postgres   Up (healthy)
flowforge-redis      redis:7-alpine       "docker-entrypoint.s…"   redis      Up (healthy)
```

---

## Step 2: Configure Host Environment Variables

When running outside the Docker network, services communicate over `localhost` rather than internal Docker DNS names (`postgres`, `redis`).

### 1. Backend Configuration (`backend/.env`)
Create or verify `backend/.env`:

```ini
# Database & Broker (Targeting Published Host Ports)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/flowforge
REDIS_URL=redis://localhost:6379/0

# Security & Tokens
JWT_SECRET=dev_secret_key_for_local_host_development_only
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=["http://localhost:3000"]

# Backoff Timeouts
RETRY_BASE_DELAY_SECONDS=5.0
RETRY_MAX_DELAY_SECONDS=60.0
```

### 2. Frontend Configuration (`frontend/.env.local`)
Create or verify `frontend/.env.local`:

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 3: Start the FastAPI Backend (Terminal 1)

1. Open **Terminal 1** in the repository root.
2. Initialize and activate a Python virtual environment:

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

3. Install backend dependencies:
```bash
pip install -r backend/requirements.txt
```

4. Run database migrations to ensure PostgreSQL schemas are up to date:
```bash
cd backend
alembic upgrade head
```

5. Launch the Uvicorn development server with hot-reload enabled:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

The API is now running at `http://127.0.0.1:8000`. You can access interactive Swagger docs at `http://127.0.0.1:8000/docs`.

---

## Step 4: Start the Celery Worker (Terminal 2)

1. Open **Terminal 2** in the repository root.
2. Activate the same virtual environment:

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

3. Start the Celery worker daemon:

```bash
# macOS / Linux (Standard Prefork Worker)
cd worker
celery -A celery_app.celery_app worker -l info -Q high,default,low
```

> [!NOTE]
> **Windows Users**: Because Windows does not support Unix process forking, Celery will raise `ValueError: not enough values to unpack`. On Windows, specify the `solo` pool:
> ```powershell
> cd worker
> celery -A celery_app.celery_app worker -l info -P solo -Q high,default,low
> ```

You will observe Celery connecting to `redis://localhost:6379/0` and registering the `high`, `default`, and `low` queue consumers.

---

## Step 5: Start the Next.js Frontend (Terminal 3)

1. Open **Terminal 3** in the repository root.
2. Navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

The administrative dashboard will start at `http://localhost:3000`. Any edits made to React components, Tailwind styling, or API clients will reflect in your browser in real time via Next.js Fast Refresh.

---

## Step 6: Verify the Complete Hybrid Stack

Run these sanity checks to ensure all five components are communicating:

1. **API Health**: Run `curl http://localhost:8000/health` $\rightarrow$ should return `{"status":"ok"}`.
2. **Dashboard**: Open `http://localhost:3000` $\rightarrow$ register an account and view the workflows list.
3. **Execution**: Trigger a workflow $\rightarrow$ observe the worker log in Terminal 2 executing tasks and Terminal 3 updating status badges dynamically.

---

## Limitations & Production Gotchas of Hybrid Mode

While hybrid mode maximizes developer velocity, keep these architectural differences in mind:

1. **Operating System Divergence**: If developing on Windows or macOS, file path separators, process signals, and Celery pooling (`solo` vs `prefork`) behave differently than the Linux-based production images.
2. **Docker Build Blindspot**: Running on the host does not validate whether `backend/Dockerfile`, `worker/Dockerfile`, or `frontend/Dockerfile` build cleanly.
3. **Internal DNS Bypass**: Inter-service networking uses `localhost` rather than Docker's embedded bridge DNS resolution (`postgres`, `redis`).

> [!IMPORTANT]
> Always execute the full containerized build (`docker compose -f infrastructure/docker-compose.yml up --build -d`) and the automated test suite before opening a Pull Request!

---

## Teardown Procedure

When you finish your development session:

1. Press `Ctrl+C` in Terminal 1, Terminal 2, and Terminal 3 to stop the host processes.
2. Stop the background infrastructure containers:
   ```bash
   # Preserves database workflows and job records
   docker compose -f infrastructure/docker-compose.yml down
   ```
   To wipe the database and queue completely, append `-v`:
   ```bash
   docker compose -f infrastructure/docker-compose.yml down -v
   ```

---

## Related Documentation & References

- [Getting Started Tutorial](../02-tutorials/getting-started.md) — Standard 5-minute containerized setup.
- [Understanding Docker Tutorial](../02-tutorials/understanding-docker.md) — Comprehensive guide to Docker networking, volumes, and Compose.
- [Running the Test Suite How-To](running-the-test-suite.md) — Running pytest and Jest suites natively.
- [Deploying to Production How-To](deploying-to-production.md) — Production release procedures.
- [Managing Dead Letters How-To](managing-dead-letters.md) — Operational inspection and requeue guide.