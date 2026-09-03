# FlowForge

FlowForge is a resilient, distributed job-processing platform designed to orchestrate asynchronous tasks, pipeline execution, and worker management at scale. It couples a responsive Next.js frontend with a high-performance FastAPI backend, backed by PostgreSQL, Redis, and Celery for distributed worker coordination.

## Setup

> **Note:** Milestone 1 establishes the initial repository skeleton and tooling. As subsequent milestones progress, detailed instructions for running database migrations, workers, and containerized environments will be updated here.

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Redis (for Celery broker / results in future milestones)
- PostgreSQL (for relational data storage in future milestones)

## Quickstart & Setup (Docker Compose)

The entire FlowForge stack (PostgreSQL, Redis, FastAPI Backend, Celery Worker, and Next.js Frontend) can be launched using Docker Compose.

### 1. Configure Environment Variables
Copy the infrastructure environment template:
```bash
cp infrastructure/.env.example infrastructure/.env
```
*(On Windows PowerShell: `Copy-Item infrastructure/.env.example infrastructure/.env`)*. Review and update `infrastructure/.env` if you want custom database credentials or secrets.

### 2. Start the Stack
Build and launch all services with health checks and automated database migrations:
```bash
docker compose -f infrastructure/docker-compose.yml up --build
```
Or in detached mode:
```bash
docker compose -f infrastructure/docker-compose.yml up --build -d
```

Once running:
- **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation & Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

### 3. Monitoring Logs & Debugging
Inspect real-time logs for any specific service (e.g., the worker or backend):
```bash
# View worker logs
docker compose -f infrastructure/docker-compose.yml logs -f worker

# View backend logs
docker compose -f infrastructure/docker-compose.yml logs -f backend
```

### 4. Teardown
To stop all services cleanly:
```bash
docker compose -f infrastructure/docker-compose.yml down
```
To stop all services and **delete all persistent volumes** (PostgreSQL database and Redis storage) for a completely fresh start:
```bash
docker compose -f infrastructure/docker-compose.yml down -v
```

---

## Running Services Individually for Debugging

If you prefer to run services manually on your host machine without containerizing every component:

### 1. Infrastructure Services (PostgreSQL & Redis)
```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres redis
```

### 2. Backend
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload
```

### 3. Celery Worker
```bash
cd worker
# Windows (requires -P solo):
..\backend\.venv\Scripts\celery -A celery_app worker -Q high,default,low --loglevel=info -P solo
# Linux/macOS:
source ../backend/.venv/bin/activate
celery -A celery_app worker -Q high,default,low --loglevel=info
```

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Testing & CI

### Backend Tests
The backend test suite uses pytest with an isolated in-memory SQLite database, synchronous in-process eager Celery execution, and respx for outbound HTTP mocking.
```bash
cd backend
# Run all tests with coverage report:
pytest --cov=app --cov=tasks --cov-report=term-missing
```

### Frontend Tests
The frontend test suite uses Jest with React Testing Library and jsdom to verify the API client's 401 refresh loop, login error handling, and role-based navigation rendering.
```bash
cd frontend
# Run Jest test suite:
npm test

# Run ESLint:
npm run lint

# Run Next.js production build check:
npm run build
```

### Continuous Integration (CI)
GitHub Actions (`.github/workflows/ci.yml`) runs on every push and pull request to `main`:
1. **Backend Tests & Coverage**: Spins up Postgres 16 and Redis 7 service containers, executes Alembic migrations, and runs pytest with coverage.
2. **Frontend Tests & Build**: Installs dependencies (`npm ci`), runs ESLint, executes Jest tests, and runs `next build`.
3. **Docker Build Validation**: Builds the `backend`, `worker`, and `frontend` Docker images in parallel to prevent build rot.

---

## Roadmap & Milestones

- [x] **Milestone 1**: Monorepo Structure & Tooling Skeleton
- [x] **Milestone 2**: Authentication & Role-Based Access Control (RBAC)
- [x] **Milestone 3**: Database Models (Workflow, Job, Task) & Schemas
- [x] **Milestone 4**: Redis & Celery Asynchronous Task Wiring
- [x] **Milestone 5**: Job Lifecycle, Task Handlers & Sequential Orchestration
- [x] **Milestone 6**: Error Handling, Retries & Exponential Backoff (Dead-Letter Handling)
- [x] **Milestone 7**: Priority Queues (High, Default, Low Tiered Routing)
- [x] **Milestone 8**: Dashboard UI (Next.js App Router, Workflows, Live Job Polling & Dead-Letter Admin)
- [x] **Milestone 9**: Full Docker & Infrastructure Orchestration (Postgres, Redis, Backend, Worker, Frontend)
- [x] **Milestone 10**: Automated Tests & CI (Pytest, Coverage, Respx, Jest, RTL, GitHub Actions Pipeline)
