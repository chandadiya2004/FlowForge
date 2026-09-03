# FlowForge

FlowForge is a resilient, distributed job-processing platform designed to orchestrate asynchronous tasks, pipeline execution, and worker management at scale. It couples a responsive Next.js frontend with a high-performance FastAPI backend, backed by PostgreSQL, Redis, and Celery for distributed worker coordination.

## Setup

> **Note:** Milestone 1 establishes the initial repository skeleton and tooling. As subsequent milestones progress, detailed instructions for running database migrations, workers, and containerized environments will be updated here.

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- Redis (for Celery broker / results in future milestones)
- PostgreSQL (for relational data storage in future milestones)

### Backend Quickstart

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the development server:
   ```bash
   uvicorn main:app --reload
   ```
5. Verify health endpoint:
   Open [http://localhost:8000/health](http://localhost:8000/health) or run:
   ```bash
   curl http://localhost:8000/health
   ```

### Frontend Quickstart

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Worker Quickstart

The worker process connects to Redis for task queuing and shares the database models and configuration directly with `backend/` by including `backend/` in `sys.path` (configured automatically in `worker/celery_app.py` and `worker/db.py`).

1. Ensure Redis is running:
   ```bash
   docker compose -f infrastructure/docker-compose.yml up -d redis
   ```
2. Navigate to the `worker/` directory:
   ```bash
   cd worker
   ```
3. Start the Celery worker listening on all three priority queues (`high,default,low`):
   ```bash
   # Windows PowerShell:
   ..\backend\.venv\Scripts\celery -A celery_app worker -Q high,default,low --loglevel=info -P solo

   # Linux / macOS:
   source ../backend/.venv/bin/activate
   celery -A celery_app worker -Q high,default,low --loglevel=info
   ```
   *(Note: `-P solo` is required on Windows to avoid OS fork limitations).*

> [!NOTE]
> **Production Deployment Note**: For local development, a single worker process monitors `-Q high,default,low` in priority order. In production (Milestone 11), dedicated worker pools are deployed per queue (e.g., separate worker instances for `high`, `default`, and `low` with distinct autoscaling policies and concurrency limits) to ensure critical jobs are never blocked by low-priority workloads.

---

## Roadmap & Milestones

- [x] **Milestone 1**: Monorepo Structure & Tooling Skeleton
- [x] **Milestone 2**: Authentication & Role-Based Access Control (RBAC)
- [x] **Milestone 3**: Database Models (Workflow, Job, Task) & Schemas
- [x] **Milestone 4**: Redis & Celery Asynchronous Task Wiring
- [x] **Milestone 5**: Job Lifecycle, Task Handlers & Sequential Orchestration
- [x] **Milestone 6**: Error Handling, Retries & Exponential Backoff (Dead-Letter Handling)
- [x] **Milestone 7**: Priority Queues (High, Default, Low Tiered Routing)
- [ ] **Milestone 8**: Real-time Status Updates (WebSockets / SSE)
- [ ] **Milestone 9**: Full Docker & Infrastructure Orchestration
- [ ] **Milestone 10**: CI/CD Pipelines & Automated Production Deployment
