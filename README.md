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

### Worker Quickstart (Preview)

1. Navigate to the `worker/` directory:
   ```bash
   cd worker
   ```
2. Start the Celery worker (requires Redis running locally or configured via `REDIS_URL`):
   ```bash
   celery -A celery_app worker --loglevel=info
   ```

---

## Roadmap & Milestones

- [x] **Milestone 1**: Monorepo Structure & Tooling Skeleton
- [ ] **Milestone 2**: Authentication & User Management
- [ ] **Milestone 3**: Database Models & Migrations
- [ ] **Milestone 4**: Job Queue & Celery Integration
- [ ] **Milestone 5**: Core API Routes & Job Lifecycle
- [ ] **Milestone 6**: Real-time Status Updates (WebSockets / SSE)
- [ ] **Milestone 7**: Frontend Dashboard & Job Management UI
- [ ] **Milestone 8**: Error Handling & Retry Policies
- [ ] **Milestone 9**: Docker & Infrastructure Orchestration
- [ ] **Milestone 10**: CI/CD Pipelines & Automated Testing
