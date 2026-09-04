# Running Locally Without Docker

While Docker Compose is the recommended way to run FlowForge as a unified system, building and restarting Docker containers on every code edit can slow down day-to-day development.

This guide explains the **hybrid development workflow**: running PostgreSQL and Redis in lightweight Docker containers (handling the infrastructure dependencies) while running the FastAPI backend, Celery worker, and Next.js frontend directly on your host machine with instant hot-reloading.

---

## Architecture of the Hybrid Setup

| Component | Where It Runs | Why |
| :--- | :--- | :--- |
| **PostgreSQL** | Docker container (`localhost:5432`) | Avoids installing and managing a local PostgreSQL server instance. |
| **Redis** | Docker container (`localhost:6379`) | Provides the message broker without needing native Redis installation. |
| **FastAPI Backend** | Host machine (`localhost:8000`) | Enables Uvicorn auto-reload (`--reload`) on Python file changes. |
| **Celery Worker** | Host machine (background process) | Allows rapid debugging and immediate inspection of task handler code. |
| **Next.js Frontend** | Host machine (`localhost:3000`) | Enables Next.js Fast Refresh for instant UI updates. |

---

## Step 1: Start PostgreSQL and Redis Containers

Use Docker Compose to start **only** the database and message broker:

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
```

Confirm both are healthy:

```bash
docker compose -f infrastructure/docker-compose.yml ps
```

Both `flowforge-postgres` and `flowforge-redis` should report `Up (healthy)`.

---

## Step 2: Configure Host Environment Variables

When services run in Docker containers, they communicate across the internal bridge network using service names like `postgres:5432` and `redis:6379`.

When running on your host machine, you must point `DATABASE_URL` and `REDIS_URL` to **`localhost`**:

### Host Environment Configuration (`backend/.env`)

Create or update `backend/.env`:

```ini
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/flowforge
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

JWT_SECRET=dev_secret_key_for_local_host_development_only
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=["http://localhost:3000"]

RETRY_BASE_DELAY_SECONDS=5.0
RETRY_MAX_DELAY_SECONDS=60.0
```

### Frontend Environment Configuration (`frontend/.env.local`)

Create or verify `frontend/.env.local`:

```ini
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## Step 3: Run the FastAPI Backend

1. Create and activate a Python virtual environment:

   ```bash
   # In root of repository
   python -m venv .venv

   # Activate virtual environment
   # On Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # On macOS / Linux:
   source .venv/bin/activate
   ```

2. Install Python dependencies:

   ```bash
   pip install -r backend/requirements.txt
   ```

3. Run database migrations:

   ```bash
   cd backend
   alembic upgrade head
   ```

4. Start the Uvicorn development server with hot-reloading enabled:

   ```bash
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

The backend is now live at `http://127.0.0.1:8000`. Any edits made in `backend/app/` will trigger an automatic server reload.

---

## Step 4: Run the Celery Worker

Open a **second terminal window**, activate the same virtual environment, and launch the Celery worker:

```bash
# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Navigate to worker directory and start worker
cd worker
celery -A celery_app.celery_app worker -l info -Q high,default,low
```

> [!NOTE]
> On Windows, if Celery reports `ValueError: not enough values to unpack`, run Celery with the `solo` pool:
> ```powershell
> celery -A celery_app.celery_app worker -l info -P solo -Q high,default,low
> ```

The worker will connect to `redis://localhost:6379/0` and listen for tasks on the `high`, `default`, and `low` priority queues.

---

## Step 5: Run the Next.js Frontend

Open a **third terminal window**, navigate to the frontend directory, and start the development server:

```bash
cd frontend
npm install
npm run dev
```

The Next.js dashboard will be available at `http://localhost:3000` with hot-module reloading enabled.

---

## When the Local Host Setup Breaks Down

While this setup is fast for code iteration, it is not an identical replica of production:

1. **Operating System Discrepancies**: If your host is Windows or macOS, path separators, file permissions, and process forking differ from the Linux containers used in production and CI.
2. **Container Build Verification**: Running on the host does not verify whether `backend/Dockerfile` or `frontend/Dockerfile` build without errors.
3. **Internal Networking**: Service-to-service DNS resolution (`postgres`, `redis`) is bypassed when using `localhost`.

> [!IMPORTANT]
> Always run the full Docker Compose stack (`docker compose -f infrastructure/docker-compose.yml up --build`) and the test suite before submitting a Pull Request!