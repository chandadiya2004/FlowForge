# CI/CD Pipeline Architecture & Quality Gates Reference

FlowForge uses **GitHub Actions** for continuous integration, automated quality gates, and container image publishing. The master workflow is defined in [.github/workflows/ci.yml](file:///d:/Edutation(P)/FlowForge/.github/workflows/ci.yml).

This document serves as an exhaustive technical specification of workflow triggers, containerized testing services, execution matrices, required repository secrets, and result evaluation rules.

---

## Pipeline Execution Topology

The CI pipeline runs unit and integration tests across backend and frontend environments in parallel before gating container image compilation and Docker Hub publishing:

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
flowchart TD
    classDef trigger fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;
    classDef service fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#faf5ff;
    classDef step fill:#1e293b,stroke:#94a3b8,stroke-width:1.5px,color:#f8fafc;
    classDef test fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;
    classDef publish fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fef2f2;
    classDef gate fill:#1e293b,stroke:#e2e8f0,stroke-width:2px,color:#f8fafc;

    Trigger([GitHub Event: Push / PR / Dispatch]):::trigger --> ParallelPhase{Parallel Test Phase}:::gate

    subgraph BackendJob ["Job 1: backend-tests (Python 3.11 on ubuntu-latest)"]
        direction TB
        subgraph ServiceContainers ["GitHub Actions Live Services"]
            PostgresSvc[("postgres:16-alpine\n(:5432) pg_isready")]:::service
            RedisSvc[("redis:7-alpine\n(:6379) redis-cli ping")]:::service
        end
        PySetup["setup-python@v5 & pip cache"]:::step
        Migrate["alembic upgrade head"]:::step
        Pytest["pytest --cov=app --cov=tasks\n(69 tests + coverage report)"]:::test
        
        ServiceContainers --> Migrate
        PySetup --> Migrate
        Migrate --> Pytest
    end

    subgraph FrontendJob ["Job 2: frontend-tests (Node.js 20 on ubuntu-latest)"]
        direction TB
        NodeSetup["setup-node@v4 & npm cache"]:::step
        NpmCI["npm ci (clean lockfile install)"]:::step
        ESLint["npm run lint (ESLint 9)"]:::step
        Jest["npm test (Jest + RTL)"]:::test
        NextBuild["npm run build (Next.js 16.3 Production Bundle)"]:::step

        NodeSetup --> NpmCI
        NpmCI --> ESLint
        ESLint --> Jest
        Jest --> NextBuild
    end

    ParallelPhase --> BackendJob
    ParallelPhase --> FrontendJob

    Pytest --> GatingGate{Both Test Jobs Succeeded?}:::gate
    NextBuild --> GatingGate

    subgraph PublishJob ["Job 3: docker-publish (needs: [backend-tests, frontend-tests])"]
        direction TB
        BuildxSetup["setup-buildx-action@v3"]:::step
        DockerLogin["docker/login-action@v3\n(if push & secrets present)"]:::step
        BuildImages["Build & Push Docker Images\n- flowforge-backend:latest\n- flowforge-worker:latest\n- flowforge-frontend:latest"]:::publish

        BuildxSetup --> DockerLogin
        DockerLogin --> BuildImages
    end

    GatingGate -->|Yes| PublishJob
    GatingGate -->|No| Blocked["Pipeline Fails & Blocks Merge"]:::publish

    style BackendJob fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f0f9ff
    style FrontendJob fill:#0f172a,stroke:#c084fc,stroke-width:1.5px,color:#faf5ff
    style PublishJob fill:#0f172a,stroke:#f87171,stroke-width:1.5px,color:#fef2f2
    style ServiceContainers fill:#0b0f19,stroke:#64748b,stroke-width:1px,color:#cbd5e1
```

---

## Workflow Triggers

The CI pipeline executes under three distinct GitHub trigger conditions:

```yaml
on:
  push:
    branches: [ main, diya-feature, "feature/**" ]
  pull_request:
    branches: [ main, diya-feature ]
  workflow_dispatch:
```

| Event Type | Target Scope | Execution Behavior |
| :--- | :--- | :--- |
| **`push`** | `main`, `diya-feature`, `feature/**` | Executes full test matrix. If pushed to `main` and credentials exist, compiles and pushes production images to Docker Hub. |
| **`pull_request`** | `main`, `diya-feature` | Executes `backend-tests`, `frontend-tests`, and runs local Docker build verification without pushing images. |
| **`workflow_dispatch`** | Any branch on-demand | Allows manual execution from the GitHub Actions dashboard for ad-hoc validation. |

---

## Detailed Job Specifications

### Job 1: `backend-tests`
- **Runner OS**: `ubuntu-latest`
- **Runtimes**: Python 3.11 with pip caching (`actions/setup-python@v5`)
- **Service Containers**:
  - **`postgres:16-alpine`**:
    - Port: `5432:5432`
    - Environment: `POSTGRES_USER: postgres`, `POSTGRES_PASSWORD: postgres`, `POSTGRES_DB: flowforge_test`
    - Health Check: `pg_isready` (interval: 10s, timeout: 5s, retries: 5)
  - **`redis:7-alpine`**:
    - Port: `6379:6379`
    - Health Check: `redis-cli ping` (interval: 10s, timeout: 5s, retries: 5)
- **Execution Steps**:
  1. Check out repository source via `actions/checkout@v4`.
  2. Set up Python 3.11 and restore pip cache.
  3. Upgrade pip and install dependencies: `pip install -r backend/requirements.txt`.
  4. Apply database migrations: `alembic upgrade head` in `backend/` against the temporary PostgreSQL service.
  5. Execute test suite with terminal coverage output:
     ```bash
     pytest --cov=app --cov=tasks --cov-report=term-missing
     ```

---

### Job 2: `frontend-tests`
- **Runner OS**: `ubuntu-latest`
- **Runtimes**: Node.js 20 with npm caching (`actions/setup-node@v4`)
- **Working Directory**: `frontend/`
- **Execution Steps**:
  1. Check out repository source via `actions/checkout@v4`.
  2. Set up Node.js 20 and configure `cache-dependency-path: frontend/package-lock.json`.
  3. Install exact dependencies using `npm ci`.
  4. Run static linting: `npm run lint` (ESLint 9).
  5. Execute Jest test suites: `npm test`.
  6. Verify production Next.js compilation:
     ```bash
     NEXT_PUBLIC_API_URL=http://localhost:8000 npm run build
     ```
     (Validates TypeScript types, React 19 JSX syntax, and static page generation).

---

### Job 3: `docker-publish`
- **Runner OS**: `ubuntu-latest`
- **Prerequisite Dependencies**: `needs: [backend-tests, frontend-tests]`
- **Execution Steps**:
  1. Check out repository source.
  2. Set up Docker Buildx via `docker/setup-buildx-action@v3`.
  3. Evaluate secrets condition: checks if `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` are present and event is not a pull request.
  4. Authenticate to Docker Hub registry via `docker/login-action@v3`.
  5. Build and push container images:
     - **Backend**: Context `backend/`, Dockerfile `backend/Dockerfile`, Tag `<username>/flowforge-backend:latest`.
     - **Worker**: Context `.`, Dockerfile `worker/Dockerfile`, Tag `<username>/flowforge-worker:latest`.
     - **Frontend**: Context `frontend/`, Dockerfile `frontend/Dockerfile`, Tag `<username>/flowforge-frontend:latest`.

---

## Required Repository Secrets

To enable automated image publishing to Docker Hub, configure these secrets under **Repository Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**:

| Secret Name | Purpose | Example Value |
| :--- | :--- | :--- |
| **`DOCKERHUB_USERNAME`** | Docker Hub account identifier | `arpanpramanik2003` |
| **`DOCKERHUB_TOKEN`** | Docker Hub Personal Access Token (PAT) with Read & Write permissions | `dckr_pat_abc123...` |

> [!NOTE]
> If repository secrets are not configured (e.g. in public forks), the `docker-publish` job gracefully skips registry authentication and builds the images locally using the tag `:ci` to verify Dockerfile syntax without failing the workflow.

---

## Interpreting CI Failures & Troubleshooting

| Failing Stage | Typical Root Cause | Actionable Remediation |
| :--- | :--- | :--- |
| **`backend-tests` $\rightarrow$ Alembic Migrations** | Missing foreign key or conflicting schema revision heads. | Run `alembic check` and verify `backend/migrations/versions/` locally before pushing. |
| **`backend-tests` $\rightarrow$ Pytest Failure** | Logic regression, broken status transition, or unhandled exception. | Run `pytest -v tests/<failing_test>.py` locally in your virtual environment. |
| **`backend-tests` $\rightarrow$ Coverage Threshold** | New functions added without corresponding test coverage. | Run `pytest --cov=app --cov=tasks --cov-report=term-missing` and add tests for uncovered lines. |
| **`frontend-tests` $\rightarrow$ ESLint** | Formatting violations or unused variables. | Run `npm run lint` in `frontend/` and fix flagged issues. |
| **`frontend-tests` $\rightarrow$ Jest** | Component snapshot mismatch or broken API client mock. | Run `npm test` in `frontend/` and inspect Jest assertion diffs. |
| **`frontend-tests` $\rightarrow$ Next.js Build** | TypeScript type errors or invalid route layouts. | Run `npm run build` locally in `frontend/` to view TypeScript compiler errors. |
| **`docker-publish` $\rightarrow$ Build Failure** | Syntax error in `Dockerfile` or missing dependency in `requirements.txt`/`package.json`. | Test locally with `docker compose -f infrastructure/docker-compose.yml build`. |

---

## Related Documentation & References

- [Git & GitHub Development Workflow](../03-how-to-guides/git-and-github-workflow.md) — Branching standards, conventional commits, and PR reviews.
- [Running the Test Suite How-To](../03-how-to-guides/running-the-test-suite.md) — Local execution instructions for pytest and Jest.
- [Deploying to Production How-To](../03-how-to-guides/deploying-to-production.md) — Multi-container production deployment using pre-built images.
- [Technology Stack Architecture](../01-introduction/tech-stack.md) — Comprehensive technical inventory.
- [REST API Reference](api-reference.md) — OpenAPI endpoint specifications.