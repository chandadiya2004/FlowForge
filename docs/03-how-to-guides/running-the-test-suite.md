# How to Run the FlowForge Automated Test Suite

FlowForge maintains automated test suites covering backend REST API endpoints, database transactions, priority queue routing, exponential backoff retries, dead-letter quarantine, and frontend React components.

This guide details how to execute tests locally, generate terminal and HTML coverage metrics, run targeted test modules, and understand testing boundaries.

---

## Test Architecture & Verification Matrix

The diagram below outlines the separation between the backend Python testing harness (`pytest`) and the frontend TypeScript testing harness (`jest`):

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
    classDef testEngine fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;
    classDef fixture fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e0e7ff;
    classDef suite fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;
    classDef report fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#faf5ff;

    subgraph BackendTesting ["Backend Test Tier (pytest & pytest-cov)"]
        PytestRunner["pytest Runner\n(Python 3.11)"]:::testEngine
        Conftest["conftest.py Fixtures\n- Isolated SQLite / PostgreSQL DB\n- CELERY_TASK_ALWAYS_EAGER=True\n- Mocked Respx HTTP Client"]:::fixture
        
        subgraph PytestSuites ["Test Suites (69 Unit & Integration Tests)"]
            AuthTests["test_auth.py\n(JWT, Passwords, RBAC)"]:::suite
            WorkflowTests["test_workflows.py & test_jobs.py\n(CRUD, Step Sequencing)"]:::suite
            QueueTests["test_priority.py & test_priority_queues.py\n(high, default, low)"]:::suite
            RetryTests["test_retry.py & test_dead_letters.py\n(Exponential Backoff & DLQ)"]:::suite
        end

        PytestReport["pytest-cov Coverage Report\n(app/ and worker/tasks/)"]:::report

        PytestRunner --> Conftest
        Conftest --> PytestSuites
        PytestSuites --> PytestReport
    end

    subgraph FrontendTesting ["Frontend Test Tier (Jest & React Testing Library)"]
        JestRunner["Jest Runner\n(Node.js 20 & JSDOM)"]:::testEngine
        JestSetup["jest.setup.ts\n- Mocked localStorage\n- Mocked window.fetch"]:::fixture

        subgraph JestSuites ["Component & Client Suites"]
            APITest["api.test.ts\n(JWT Header Injection & 401 Refresh)"]:::suite
            LoginTest["login.test.tsx\n(Form Validation & Error States)"]:::suite
            NavTest["navbar.test.tsx\n(Role-Based Nav Links)"]:::suite
        end

        JestReport["Jest Coverage Summary\n(Statements, Branches, Lines)"]:::report

        JestRunner --> JestSetup
        JestSetup --> JestSuites
        JestSuites --> JestReport
    end

    style BackendTesting fill:#0f172a,stroke:#38bdf8,stroke-width:1.5px,color:#f0f9ff
    style FrontendTesting fill:#0f172a,stroke:#c084fc,stroke-width:1.5px,color:#faf5ff
    style PytestSuites fill:#0b0f19,stroke:#334155,stroke-width:1.5px,color:#e2e8f0
    style JestSuites fill:#0b0f19,stroke:#334155,stroke-width:1.5px,color:#e2e8f0
```

---

## 1. Running Backend Tests (`pytest`)

The backend test suite ([backend/tests/](file:///d:/Edutation(P)/FlowForge/backend/tests/)) validates API routes, authentication gates, priority routing, worker execution, and database models.

### Isolated In-Process Execution (Eager Celery)
In [backend/tests/conftest.py](file:///d:/Edutation(P)/FlowForge/backend/tests/conftest.py), Celery is configured for synchronous in-memory testing:
```python
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)
```
This forces tasks to execute synchronously within the test process, allowing full assertion of state changes without needing an external Redis broker running.

### Prerequisites
Activate your virtual environment and ensure dependencies are installed:
```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt

# macOS / Linux
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### Run All 69 Backend Tests
Navigate to the `backend/` directory and run:
```bash
cd backend
pytest -v
```

### Run with Terminal Coverage Report
To execute the suite and output line-by-line coverage metrics across both `backend/app/` and `worker/tasks/`:
```bash
cd backend
pytest --cov=app --cov=tasks --cov-report=term-missing
```

### Run Specific Test Modules
You can target specific feature areas to speed up local test cycles:

```bash
# Authentication & Role-Based Access Control
pytest tests/test_auth.py -v

# Workflows and Job Creation
pytest tests/test_workflows.py tests/test_jobs.py -v

# Priority Queue Routing (high, default, low)
pytest tests/test_priority.py tests/test_priority_queues.py -v

# Exponential Backoff Retries
pytest tests/test_retry.py -v

# Dead-Letter Queue Quarantine & Requeuing
pytest tests/test_dead_letters.py -v
```

### Running Tests Against a Live PostgreSQL Service
To test against a real PostgreSQL container rather than an in-memory SQLite database:
```bash
# Ensure postgres container is running
docker compose -f infrastructure/docker-compose.yml up -d postgres

# Run pytest passing the container connection string
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/flowforge pytest -v
```

---

## 2. Running Frontend Tests (`Jest`)

The frontend test suite in [frontend/__tests__/](file:///d:/Edutation(P)/FlowForge/frontend/__tests__/) verifies client-side authentication, automatic JWT refresh retry loops, and accessible UI component rendering.

### Prerequisites
Ensure frontend dependencies are installed:
```bash
cd frontend
npm install
```

### Run All Frontend Tests
```bash
cd frontend
npm test
```

### Run with Coverage Metrics
Generate a full coverage table analyzing statement, branch, and function coverage:
```bash
cd frontend
npm test -- --coverage
```

### Run in Interactive Watch Mode
To auto-rerun tests when editing React components:
```bash
cd frontend
npm test -- --watch
```

---

## 3. Running Backend Tests Inside Docker (Clean Room)

If you want to execute tests inside the exact Linux container environment used in production:

```bash
# Ensure services are up
docker compose -f infrastructure/docker-compose.yml up -d

# Execute pytest directly inside the backend container
docker compose -f infrastructure/docker-compose.yml exec backend pytest -v --cov=app --cov=tasks
```

---

## Test Coverage Matrix

| Feature Area | Test Files | Tested Capabilities |
| :--- | :--- | :--- |
| **Authentication & RBAC** | `tests/test_auth.py` | Bcrypt password hashing, JWT creation/verification, refresh token rotation, expired token rejection, `admin`/`member`/`viewer` role enforcement. |
| **Workflows & Jobs** | `tests/test_workflows.py`<br>`tests/test_jobs.py` | Workflow JSON schema validation, task record creation, state transitions (`pending` $\rightarrow$ `running` $\rightarrow$ `completed`), duplicate sequence prevention. |
| **Priority Queueing** | `tests/test_priority.py`<br>`tests/test_priority_queues.py` | Integer priority mapping to `high` (1–3), `default` (4–7), and `low` (8–10) queues; Celery queue assignment. |
| **Retries & Backoff** | `tests/test_retry.py` | Retry count incrementing, exponential backoff calculation ($\min(\text{base} \times 2^{\text{retry}-1}, \text{max})$), Celery countdown re-dispatch. |
| **Dead-Letter Queue** | `tests/test_dead_letters.py` | Quarantine into `dead_letter_tasks` upon retry exhaustion, admin filtering by workflow, atomic task reset on requeue. |
| **Frontend API Client** | `__tests__/api.test.ts` | Bearer token header injection, transparent 401 token refresh retry, logout on token invalidation. |
| **Frontend UI Components**| `__tests__/login.test.tsx`<br>`__tests__/navbar.test.tsx` | Login form validation, error message rendering, role-conditional navigation links. |

---

## Automated Quality Gates in CI/CD

Every commit and pull request triggers the automated GitHub Actions CI workflow defined in [.github/workflows/ci.yml](file:///d:/Edutation(P)/FlowForge/.github/workflows/ci.yml):

- **`backend-tests`**: Spins up temporary PostgreSQL 16 and Redis 7 service containers, runs Alembic migrations, and enforces code coverage via `pytest --cov`.
- **`frontend-tests`**: Provisions Node.js 20, runs ESLint (`npm run lint`), executes Jest suites (`npm test`), and validates the production Next.js build (`npm run build`).

> [!IMPORTANT]
> Pull Requests cannot be merged if any test fails or if coverage drops below established thresholds.

---

## Related Documentation & References

- [CI/CD Pipeline Reference](../04-reference/ci-cd-pipeline.md) — GitHub Actions pipeline stages and service container configurations.
- [Git & GitHub Development Workflow](git-and-github-workflow.md) — Feature-branch conventions, conventional commits, and PR standards.
- [Running Locally Without Docker](running-locally-without-docker.md) — Hybrid local workflow for fast developer feedback.
- [Retry & Dead-Letter Strategy](../05-explanation/retry-and-dead-letter-strategy.md) — Detailed mathematical and architectural specifications of retry mechanics.
- [Priority Queue Design](../05-explanation/priority-queue-design.md) — Priority partitioning rules across Redis channels.