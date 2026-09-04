# CI/CD Pipeline Reference

FlowForge uses **GitHub Actions** for continuous integration and automated quality assurance. The pipeline is defined in [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml).

This document explains the trigger conditions, job specifications, service container topologies, and result interpretation rules.

---

## Pipeline Overview & Triggers

The CI pipeline runs automatically under three conditions:

```yaml
on:
  push:
    branches: [ main, diya-feature, "feature/**" ]
  pull_request:
    branches: [ main, diya-feature ]
  workflow_dispatch:
```

1. **Pushes**: Any commit pushed to `main`, `diya-feature`, or any branch matching `feature/**`.
2. **Pull Requests**: Any PR targeting `main` or `diya-feature`.
3. **Manual Trigger (`workflow_dispatch`)**: Can be executed manually on demand from the GitHub Actions web interface.

All three jobs execute **in parallel** on `ubuntu-latest` virtual runners to minimize feedback latency.

---

## Pipeline Jobs

```mermaid
flowchart TD
    Trigger([Push / Pull Request / Dispatch]) --> JobA[Job 1: backend-tests\n(Python 3.11)]
    Trigger --> JobB[Job 2: frontend-tests\n(Node.js 20)]
    Trigger --> JobC[Job 3: docker-build-check\n(Docker Buildx)]

    subgraph BackendJob["backend-tests"]
        S1[(Postgres 16 Service)] --- S2[(Redis 7 Service)]
        S1 --> M1[Alembic Migrations]
        S2 --> M1
        M1 --> T1[pytest with Coverage]
    end

    subgraph FrontendJob["frontend-tests"]
        F1[ESLint Check] --> F2[Jest Unit Tests]
        F2 --> F3[Next.js Production Build]
    end

    subgraph DockerJob["docker-build-check"]
        D1[Build Backend Dockerfile]
        D2[Build Worker Dockerfile]
        D3[Build Frontend Dockerfile]
    end

    JobA --> BackendJob
    JobB --> FrontendJob
    JobC --> DockerJob
```

---

### 1. `backend-tests` (Backend Tests & Coverage)
Validates backend database operations, API route handling, Celery tasks, and code coverage.

- **Service Containers**:
  - **`postgres:16-alpine`**: Spins up an isolated database instance (`flowforge_test`) on port `5432` with an active health check (`pg_isready`).
  - **`redis:7-alpine`**: Spins up an isolated message broker on port `6379` with a health check (`redis-cli ping`).
- **Steps**:
  1. Checks out repository source via `actions/checkout@v4`.
  2. Sets up Python 3.11 with pip package caching via `actions/setup-python@v5`.
  3. Installs backend dependencies from `backend/requirements.txt`.
  4. Runs database migrations: `alembic upgrade head` against the PostgreSQL service container.
  5. Executes the full backend test suite with terminal coverage reporting:
     ```bash
     pytest --cov=app --cov=tasks --cov-report=term-missing
     ```

---

### 2. `frontend-tests` (Frontend Tests & Build)
Validates TypeScript syntax, code style, component logic, and Next.js bundle compilation.

- **Steps** (executed inside `frontend/`):
  1. Checks out repository source via `actions/checkout@v4`.
  2. Sets up Node.js 20 with npm dependency caching via `actions/setup-node@v4`.
  3. Installs clean locked dependencies using `npm ci`.
  4. Runs code linting: `npm run lint` (ESLint).
  5. Executes React component and API client test suites: `npm test` (Jest).
  6. Compiles production Next.js build:
     ```bash
     npm run build
     ```
     (Ensures there are no missing imports, syntax errors, or broken route layouts).

---

### 3. `docker-publish` (Docker Build & Push to Docker Hub)
Builds production container images and, upon branch push with configured credentials, publishes them directly to Docker Hub registry.

- **Steps**:
  1. Checks out repository source via `actions/checkout@v4`.
  2. Sets up Docker Buildx via `docker/setup-buildx-action@v3`.
  3. Authenticates to Docker Hub using repository secrets (`DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`) via `docker/login-action@v3`.
  4. Builds and publishes all three images to Docker Hub using `docker/build-push-action@v5`:
     - `${{ secrets.DOCKERHUB_USERNAME }}/flowforge-backend:latest`
     - `${{ secrets.DOCKERHUB_USERNAME }}/flowforge-worker:latest`
     - `${{ secrets.DOCKERHUB_USERNAME }}/flowforge-frontend:latest`
  5. On pull requests or when secrets are omitted, builds are validated locally without publishing.

---

## How to Read CI Results

### On Pull Requests
GitHub displays the status of all three checks at the bottom of the PR conversation page:

- **Green Checkmark (Passed)**: All tests passed, migrations applied successfully, coverage metrics were generated, and Docker builds succeeded.
- **Red "X" (Failed)**: One or more steps failed. Click **"Details"** next to the failing check to expand the exact step log and examine the traceback.

> [!IMPORTANT]
> **Branch Protection Policy**: Pull Requests should **never** be merged with a red CI check. All three jobs (`backend-tests`, `frontend-tests`, `docker-publish`) must report green before merging into `main`.

### In the GitHub Actions Tab
1. Click the **"Actions"** tab at the top of the GitHub repository.
2. Select **"FlowForge CI"** in the left sidebar to view the chronological run history.
3. Click into any specific workflow run to view the interactive timeline graph, execution durations, and container publishing logs.

---

## Deployment & Image Publishing Status

> [!NOTE]
> FlowForge now **automatically builds and publishes production container images to Docker Hub** on verified pushes. 
> 
> The next milestone (Milestone 11) will extend this pipeline to trigger live cloud container deployments (e.g. AWS ECS / Render / Fly.io). For production guidance, see [Deploying to Production](../03-how-to-guides/deploying-to-production.md).