# Getting Started

This guide walks you through setting up and running FlowForge from scratch using Docker Compose. By the end of this tutorial, you will have all five services—PostgreSQL, Redis, the FastAPI backend, the Celery background worker, and the Next.js dashboard—running locally and verified.

---

## Prerequisites

Before starting, ensure you have the following tools installed on your host machine:

| Tool | Recommended Version | Why It Is Needed |
| :--- | :--- | :--- |
| **Docker Desktop** | 4.25+ (Docker Engine 24+, Compose v2) | Runs all five FlowForge services in isolated containers with configured networking and health checks. You do not need PostgreSQL, Redis, or Celery installed natively. |
| **Git** | 2.30+ | Required to clone the FlowForge repository and manage branch checkouts. |
| **Node.js** *(Optional)* | 18+ or 20+ LTS | Only needed if you plan to run frontend development servers or the Jest test suite natively on your host machine outside Docker. |
| **Python** *(Optional)* | 3.11+ | Only needed if you plan to execute backend unit tests (`pytest`) or run database migrations natively on your host machine outside Docker. |

---

## Step-by-Step Setup

### Step 1: Clone the Repository

Clone the FlowForge repository to your local machine and navigate into the root directory:

```bash
git clone https://github.com/chandadiya2004/FlowForge.git
cd FlowForge
```

---

### Step 2: Configure Environment Variables

FlowForge uses environment variables to manage database credentials, JWT secrets, network origins, and backoff timeouts.

Copy the template from `infrastructure/.env.example` to create `infrastructure/.env`:

```bash
# On Linux / macOS / Git Bash
cp infrastructure/.env.example infrastructure/.env

# On Windows (PowerShell)
Copy-Item infrastructure/.env.example infrastructure/.env
```

Open `infrastructure/.env` in your text editor. For local development, the default values are pre-configured to work out of the box:

```ini
# PostgreSQL Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=flowforge

# Redis Broker
REDIS_URL=redis://redis:6379/0

# Security & Authentication
JWT_SECRET=flowforge_super_secret_jwt_key_change_in_production
JWT_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:3000

# Retries & Backoff Configuration
RETRY_BASE_DELAY_SECONDS=10.0
RETRY_MAX_DELAY_SECONDS=300.0

# Frontend Browser-Facing API URL
NEXT_PUBLIC_API_URL=http://localhost:8000
```

> [!TIP]
> If you decide to change `POSTGRES_PASSWORD` or `POSTGRES_DB`, Docker Compose will automatically propagate those values into the backend and worker service connection strings.

---

---

### Step 3: Launch FlowForge

You can launch FlowForge in one of two ways depending on whether you want to run pre-built containers or build local code:

#### Option A: Quick Launch with Pre-Built Docker Hub Images (Fastest — Ready in ~30s)
> **Recommended for:** Quick evaluations, demoing, or running FlowForge without needing compilers, Node.js, or Python on your computer.

```bash
docker compose -f docker-compose.prod.yml up -d
```

**What Docker Does & Expected Terminal Output:**
Docker contacts Docker Hub, downloads the pre-built images for your architecture, provisions the isolated network and volumes, and boots all five services:

```text
[+] Running 8/8
 ✔ Network flowforge_network             Created
 ✔ Volume "flowforge_postgres_data"      Created
 ✔ Volume "flowforge_redis_data"         Created
 ✔ Container flowforge-postgres          Healthy
 ✔ Container flowforge-redis             Healthy
 ✔ Container flowforge-backend           Started
 ✔ Container flowforge-worker            Started
 ✔ Container flowforge-frontend          Started
```

---

#### Option B: Build from Source (For Developers & Contributors)
> **Recommended for:** Anyone modifying backend Python code, Celery worker tasks, or Next.js frontend pages.

```bash
docker compose -f infrastructure/docker-compose.yml up --build -d
```

**What Docker Does & Expected Terminal Output:**
The `--build` flag instructs Docker to read `backend/Dockerfile`, `worker/Dockerfile`, and `frontend/Dockerfile`, copy your local code, install dependencies, compile the Next.js production bundle, and start all containers:

```text
[+] Building 35.2s (32/32) FINISHED
 => [backend internal] load build definition from Dockerfile
 => [worker internal] load build definition from Dockerfile
 => [frontend internal] load build definition from Dockerfile
 => => transferring dockerfile: 520B
...
[+] Running 8/8
 ✔ Network flowforge_network             Created
 ✔ Volume "flowforge_postgres_data"      Created
 ✔ Volume "flowforge_redis_data"         Created
 ✔ Container flowforge-postgres          Healthy
 ✔ Container flowforge-redis             Healthy
 ✔ Container flowforge-backend           Started
 ✔ Container flowforge-worker            Started
 ✔ Container flowforge-frontend          Started
```

---

### Step 4: Confirm All Containers Are Running & Healthy

Verify the status of all five services:

```bash
# If you launched Option A:
docker compose -f docker-compose.prod.yml ps

# If you launched Option B:
docker compose -f infrastructure/docker-compose.yml ps
```

**Expected Output:**
```text
NAME                 IMAGE                                         SERVICE    STATUS
flowforge-postgres   postgres:16-alpine                            postgres   Up (healthy)
flowforge-redis      redis:7-alpine                                redis      Up (healthy)
flowforge-backend    arpanpramanik2003/flowforge-backend:latest    backend    Up
flowforge-worker     arpanpramanik2003/flowforge-worker:latest     worker     Up
flowforge-frontend   arpanpramanik2003/flowforge-frontend:latest   frontend   Up
```

All five services should report `Up`. If `flowforge-postgres` and `flowforge-redis` display `(healthy)`, the system is ready to process traffic.

---

## Verify It Worked

Verify each core component using your browser or terminal:

### 1. Web Dashboard
Open your browser and navigate to:
```
http://localhost:3000
```
You should see the FlowForge landing screen with navigation buttons for **Login**, **Register**, and **Workflows**.

### 2. Backend API Health Check
Open your browser or run `curl` against the FastAPI health check endpoint:
```bash
curl http://localhost:8000/health
```
**Expected Response:**
```json
{"status": "ok"}
```

### 3. Interactive API Documentation (OpenAPI / Swagger)
FastAPI automatically publishes interactive API documentation:
```
http://localhost:8000/docs
```
You can inspect and execute requests against all auth, workflow, job, and dead-letter endpoints directly from this interface.

### 4. Background Worker Connectivity
View the worker logs to verify that Celery successfully connected to Redis and registered the tiered queues (`high`, `default`, `low`):

```bash
docker compose -f infrastructure/docker-compose.yml logs -f worker
```

Look for lines indicating active queues and registered tasks:
```text
[tasks]
  . execute_task
  . ping

[queues]
  . high
  . default
  . low
```

---

## Troubleshooting First-Run Issues

### Problem 1: Port Already in Use (`bind: address already in use`)
- **Cause**: A local instance of PostgreSQL (port `5432`), Redis (port `6379`), an existing Node app (port `3000`), or another web server (port `8000`) is already running natively on your host machine.
- **Solution**:
  - Stop your local services:
    - **Windows**: Stop the Postgres/Redis service via the Services manager (`services.msc`).
    - **macOS / Linux**: `sudo systemctl stop postgresql redis` or `brew services stop postgresql redis`.
  - Alternatively, edit the host port mappings in `infrastructure/docker-compose.yml` (e.g. change `"5432:5432"` to `"5433:5432"`).

---

### Problem 2: Backend Container Exits Immediately with Migration Failure
- **Cause**: The backend attempted to run `alembic upgrade head` before PostgreSQL was ready to accept incoming TCP connections.
- **Solution**:
  FlowForge's `docker-compose.yml` includes health checks (`condition: service_healthy`) to prevent this. However, on machines under heavy load, the initial database cluster initialization may take longer than the default timeout.
  1. Inspect the backend logs:
     ```bash
     docker compose -f infrastructure/docker-compose.yml logs backend
     ```
  2. Restart the backend after Postgres completes its initialization:
     ```bash
     docker compose -f infrastructure/docker-compose.yml restart backend
     ```

---

### Problem 3: CORS or Authentication Failures in Browser
- **Cause**: The frontend cannot communicate with the backend because `NEXT_PUBLIC_API_URL` or `CORS_ORIGINS` is misconfigured.
- **Solution**:
  Ensure that in `infrastructure/.env`:
  - `NEXT_PUBLIC_API_URL=http://localhost:8000` (this is accessed from the user's host browser, **not** from inside the container network).
  - `CORS_ORIGINS=http://localhost:3000`.
  After changing these values, rebuild the frontend container:
  ```bash
  docker compose -f infrastructure/docker-compose.yml up --build -d frontend
  ```

---

## Stopping the Platform

When you are finished working:

- **Stop containers while preserving database and queue data**:
  ```bash
  docker compose -f infrastructure/docker-compose.yml down
  ```

- **Stop containers and completely wipe all database and queue volumes**:
  ```bash
  docker compose -f infrastructure/docker-compose.yml down -v
  ```