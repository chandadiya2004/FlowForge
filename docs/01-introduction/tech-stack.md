# Tech Stack

This document details every technology, framework, and tool actively used in FlowForge. For each technology, we explain what it is, why it was chosen specifically for this architecture, and its concrete role in the codebase.

---

## Backend & Asynchronous Runtime

### 1. FastAPI
- **What it is**: A modern, high-performance Python web framework for building APIs based on standard Python type hints and ASGI.
- **Why it was chosen**: FlowForge requires strict schema validation for arbitrary workflow task definitions and JSON payloads, along with fast request parsing and automated OpenAPI/Swagger documentation. FastAPI's integration with Pydantic provides native request validation and serialization with zero boilerplate, allowing the API layer to reject malformed workflow payloads before touching the database or message broker.
- **Role in FlowForge**: Powers the entire REST API (`backend/main.py`, `backend/app/api/`). It handles user authentication, workflow CRUD operations, job triggering, task status queries, and dead-letter review endpoints.

---

### 2. SQLAlchemy + Alembic
- **What it is**: SQLAlchemy is an Object Relational Mapper (ORM) and SQL toolkit for Python, and Alembic is its lightweight database migration management tool.
- **Why it was chosen**: FlowForge manages complex relational dependencies across users, workflows, jobs, sequential tasks, and dead-letter entries with strict foreign key constraints and cascading behaviors (e.g., deleting a workflow removes its associated jobs and tasks). Alembic ensures predictable, trackable schema evolution across development environments, automated CI test databases, and production container rollouts without manual SQL intervention.
- **Role in FlowForge**: SQLAlchemy defines the declarative models in `backend/app/models/` and handles all database queries and transactions. Alembic maintains migration scripts in `backend/alembic/`, running schema upgrades automatically on container startup.

---

### 3. PostgreSQL
- **What it is**: An enterprise-grade, open-source object-relational database management system known for reliability, transactional integrity, and strong ACID guarantees.
- **Why it was chosen**: Distributed job orchestration cannot tolerate race conditions or corrupted intermediate state. FlowForge requires transactions, row-level locking, foreign key integrity, and native JSON support (storing variable task input/output configurations). PostgreSQL provides the durability required so that if a worker or host crashes midway through a task, the pipeline state remains intact and auditable.
- **Role in FlowForge**: Acts as the primary system of record. It stores user accounts, workflow templates, job states, task executions, and dead-letter records (`flowforge-postgres` container on port `5432`).

---

### 4. Redis
- **What it is**: An in-memory, open-source key-value data store used primarily as a message broker and caching engine.
- **Why it was chosen**: Celery requires an external message broker to transport job messages asynchronously between the API server and worker processes. Redis offers ultra-low latency, trivial containerized setup, and native list/set primitives suited for Celery queues without the operational overhead and memory footprint of heavier brokers like RabbitMQ or Kafka.
- **Role in FlowForge**: Serves strictly as the **Celery message broker and result backend** (`flowforge-redis` container on port `6379`). It is **not** used for general application caching or session storage in this project; its sole duty is hosting Celery task queues (`high`, `default`, `low`) and task execution results.

---

### 5. Celery
- **What it is**: A distributed asynchronous task and job queue system for Python focused on real-time processing and task scheduling.
- **Why it was chosen**: FlowForge is fundamentally a background job processor. Tasks must execute outside of the HTTP request-response cycle, support configurable execution countdowns (delays for exponential backoff retries), and distribute work across scalable worker nodes. Because Redis does not natively support fine-grained numeric priority queues the way RabbitMQ does, we leveraged Celery's multi-queue capabilities to route jobs into tiered priority queues (`high`, `default`, `low`).
- **Role in FlowForge**: Manages task distribution and execution lifecycle (`worker/celery_app.py`, `worker/tasks/`). Worker processes consume tasks from Redis queues, invoke handlers (`log_message`, `sleep`, `http_call`), perform retries with backoff, record failures to dead-letter tables, and coordinate subsequent pipeline steps.

---

### 6. JWT (`python-jose`) + `passlib`
- **What it is**: `python-jose` is a JavaScript Object Signing and Encryption (JOSE) implementation in Python, and `passlib` is a password hashing library utilizing `bcrypt`.
- **Why it was chosen**: Stateless token-based authentication avoids database lookups for session validation on every authenticated API request. Passlib with bcrypt ensures one-way cryptographically secure salted password hashing against brute-force attacks.
- **Role in FlowForge**: `passlib` securely hashes and verifies user passwords on signup and login (`backend/app/core/security.py`). `python-jose` signs and validates short-lived access JWTs and longer-lived refresh tokens, embedding user identity and role claims (`admin`, `member`, `viewer`) for RBAC enforcement.

---

## Frontend & Interface

### 7. Next.js + TypeScript
- **What it is**: Next.js is a React framework for building server-rendered and client-rendered web applications; TypeScript adds static type definitions to JavaScript.
- **Why it was chosen**: The FlowForge dashboard requires both static structure and interactive client components for real-time polling, form validation, and reactive status changes. Next.js App Router provides structured file-based routing and fast client transitions, while TypeScript ensures API contract consistency between backend schema models and frontend view states.
- **Role in FlowForge**: Powers the dashboard UI (`frontend/src/app/`). Provides views for login/registration, workflow authoring, real-time job execution polling, task log inspection, and dead-letter review.

---

### 8. Tailwind CSS
- **What it is**: A utility-first CSS framework for rapid user interface styling directly within markup.
- **Why it was chosen**: FlowForge required a clean, responsive, and maintainable dashboard interface without bloated CSS files or heavy third-party UI component libraries that add runtime overhead and configuration friction.
- **Role in FlowForge**: Styles all frontend components, forms, tables, status badges (e.g., color-coded job statuses like `completed`, `running`, `failed`), and layouts across `frontend/src/app/`.

---

## Infrastructure & DevOps

### 9. Docker + Docker Compose
- **What it is**: Docker packages software into isolated container images, and Docker Compose coordinates multi-container Docker applications.
- **Why it was chosen**: FlowForge consists of five interdependent services: PostgreSQL, Redis, FastAPI, Celery Worker, and Next.js. Without containerization, local onboarding and production parity would require manual setup of Python virtual environments, Node dependencies, PostgreSQL databases, and Redis servers. Docker Compose allows any developer to spin up the entire platform in a single command (`docker compose up --build`).
- **Role in FlowForge**: Defined in `infrastructure/docker-compose.yml`. Manages container builds, service health checks (e.g., waiting for PostgreSQL and Redis to be healthy before starting FastAPI and Celery), container networking (`flowforge_network`), and persistent data volumes (`postgres_data`, `redis_data`).

---

### 10. GitHub Actions
- **What it is**: A continuous integration and continuous delivery (CI/CD) automation platform integrated directly into GitHub repositories.
- **Why it was chosen**: Automated verification is essential to prevent regressions in task orchestration, database migrations, and authentication. Having a dedicated CI pipeline ensures every pull request passes all unit tests, integration tests, and coverage criteria before merging into main branches.
- **Role in FlowForge**: Configured in `.github/workflows/ci.yml`. Runs on every push and pull request, executing:
  - Backend linting, migration checks, and `pytest` with code coverage reports.
  - Frontend TypeScript verification, linting, and `jest` component tests.

---

## Testing Frameworks

### 11. pytest + pytest-cov
- **What it is**: `pytest` is a mature Python testing framework, and `pytest-cov` is a plugin that measures code coverage during test runs.
- **Why it was chosen**: FlowForge requires rigorous testing of edge cases: synchronous and eager Celery execution, token expiration, database transactions, exponential backoff math, and role authorization. Pytest's fixture system allows spinning up isolated in-memory test databases and mocking external HTTP requests seamlessly via `httpx` and `respx`.
- **Role in FlowForge**: Runs the backend test suite in `backend/tests/` (69 tests covering auth, workflows, jobs, tasks, priority routing, retries, and dead letters). Enforces strict test coverage thresholds in CI.

---

### 12. Jest + React Testing Library
- **What it is**: Jest is a JavaScript test runner, and React Testing Library is a testing utility that verifies React components from the end-user's perspective.
- **Why it was chosen**: The dashboard needs automated verification for critical user journeys—login form submission, token storage, API error toast rendering, and polling state transitions—without requiring a full end-to-end browser runtime in CI.
- **Role in FlowForge**: Executes frontend unit and integration tests (`frontend/src/__tests__/`). Verifies authentication flows, route transitions, and UI status rendering.