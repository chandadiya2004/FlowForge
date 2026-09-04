# Project Roadmap

This roadmap tracks the development progression of FlowForge across all 12 core milestones. Statuses represent the current operational state of the codebase.

---

## Development Milestones

| Milestone | Subsystem | Description | Status |
| :---: | :--- | :--- | :---: |
| **M1** | **Project Skeleton & Setup** | Project directory structure, FastAPI foundation, Next.js starter, and initial Git repository layout. | `Completed` |
| **M2** | **Authentication & RBAC** | User registration, bcrypt password hashing, stateless JWT access/refresh token rotation, and role guards (`admin`, `member`, `viewer`). | `Completed` |
| **M3** | **Data Models & CRUD** | Relational schemas for `User`, `Workflow`, `Job`, and `Task` with SQLAlchemy ORM, Alembic migrations, and REST endpoints. | `Completed` |
| **M4** | **Async Broker Plumbing** | Redis message broker integration, Celery client configuration, worker app wiring, and verification ping tasks. | `Completed` |
| **M5** | **Job Execution Engine** | Task registry pattern (`log_message`, `sleep`, `http_call`), linear sequential execution, and dynamic pipeline orchestration. | `Completed` |
| **M6** | **Retry & Dead-Lettering** | Automated task retries with exponential backoff countdowns and permanent failure isolation in `dead_letter_tasks`. | `Completed` |
| **M7** | **Priority Queues** | Job priority mapping (1–10) routed to tiered Celery queues (`high`, `default`, `low`) consumed in strict priority order. | `Completed` |
| **M8** | **Next.js Dashboard** | Interactive dashboard for authentication, workflow management, live job execution monitoring, and dead-letter review. | `Completed` |
| **M9** | **Docker Compose Stack** | Unified multi-container deployment orchestrating PostgreSQL 16, Redis 7, FastAPI, Celery Worker, and Next.js with health checks. | `Completed` |
| **M10** | **Automated Tests & CI** | Comprehensive `pytest` backend test suite (93% coverage) and `jest` frontend suite running in GitHub Actions. | `Completed` |
| **DOCS** | **Documentation Suite** | Scannable, verified documentation covering tutorials, guides, references, and architectural explanations. | `Completed` |
| **M11** | **Production Cloud Deployment** | Cloud infrastructure provisioning, container registry publishing, production secrets management, and automated deploy workflows. | `Not Started` |
| **M12** | **Load Testing & Benchmarking** | High-concurrency worker stress testing, Redis queue saturation benchmarks, and database bottleneck profiling. | `Not Started` |

---

## Current Status Summary

With the completion of **Milestone 10** and the full **Documentation Pass**:
- The core platform is completely functional, containerized, covered by automated unit and integration tests, and validated in CI on every push.
- The next development cycle will focus on **Milestone 11 (Production Cloud Deployment)** and **Milestone 12 (High-Concurrency Load Testing)**.