# Running the Test Suite

FlowForge maintains automated test suites covering backend API routes, Celery task execution, database transactions, and frontend client logic.

This guide provides instructions for running tests locally, generating coverage metrics, and understanding test boundaries.

---

## 1. Running Backend Tests (pytest)

The backend test suite is written using `pytest` and uses an isolated test database (`flowforge_test` or SQLite in-memory) configured in `backend/tests/conftest.py`.

During testing, Celery is automatically configured with:
```python
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
```
This forces tasks to execute synchronously in-process without requiring a live Redis broker.

### Prerequisites
Ensure your Python virtual environment is active and test dependencies are installed:
```bash
# In backend/ directory or root with venv active
pip install -r backend/requirements.txt
```

### Run All Backend Tests
Navigate to the `backend/` directory and execute `pytest`:

```bash
cd backend
pytest -v
```

### Run with Code Coverage
To run the full suite and generate a terminal code coverage report across both `app/` and worker `tasks/`:

```bash
cd backend
pytest --cov=app --cov=tasks --cov-report=term-missing
```

### Run Specific Test Modules
You can run targeted test files or individual test cases:

```bash
# Run only authentication and RBAC tests
pytest tests/test_auth.py -v

# Run only retry and exponential backoff tests
pytest tests/test_retry.py -v

# Run only dead-letter queue tests
pytest tests/test_dead_letters.py -v

# Run only priority queue routing tests
pytest tests/test_priority.py tests/test_priority_queues.py -v
```

---

## 2. Running Frontend Tests (Jest)

The frontend test suite uses `jest` and `@testing-library/react` to verify authentication flows, API client token refreshing, and navigation components.

### Prerequisites
Ensure Node dependencies are installed:
```bash
cd frontend
npm install
```

### Run All Frontend Tests
From the `frontend/` directory, run:

```bash
npm test
```

### Run with Coverage
To inspect frontend component test coverage:

```bash
npm test -- --coverage
```

### Run in Watch Mode (Interactive Development)
```bash
npm test -- --watch
```

---

## What Is Covered vs. What Is Not

To maintain realistic expectations, understand what our current test suite covers and where future testing milestones will focus:

### What Is Covered (69 Backend Tests + 3 Frontend Suites)
- **Authentication & RBAC**: Password hashing, JWT token issuance, refresh token rotation, expired token rejection, and role-based permissions (`admin`, `member`, `viewer`).
- **Workflow & Job Lifecycle**: Creating workflows, unpacking step lists into sequential task records, tracking job status transitions (`pending` $\rightarrow$ `running` $\rightarrow$ `completed` / `failed`), and preventing invalid state transitions.
- **Priority Queue Routing**: Validation that job priorities (1–10) accurately map to the `high` (1–3), `default` (4–7), and `low` (8–10) Celery queues.
- **Retry Logic & Exponential Backoff**: Verification that failed tasks increment `retry_count`, enter `retrying` status, calculate correct backoff delays ($\text{base} \times 2^{\text{attempt}-1}$), and cap at max delay limits.
- **Dead-Letter Handling**: Creation of `DeadLetterTask` records upon retry exhaustion, admin listing/filtering endpoints, and atomic task requeuing.
- **Frontend Core Logic**: API client header injection, automatic 401 refresh retry, login form validation, and role-conditional navigation links.

### What Is NOT Covered Yet
- **End-to-End (E2E) Browser Tests**: Automated browser testing tools (such as Playwright or Cypress) that open real browser instances to simulate multi-page user interactions are not yet implemented.
- **High-Concurrency Load Testing**: Stress tests simulating thousands of simultaneous Celery tasks or measuring Redis broker throughput under saturated conditions are planned for future performance milestones.

---

## Automated Testing in CI/CD

You do not need to rely solely on local testing. Every commit and pull request triggers our automated GitHub Actions workflow (`.github/workflows/ci.yml`), which executes:
1. **`backend-tests`**: Spins up temporary PostgreSQL and Redis service containers, runs Alembic migrations, and executes `pytest --cov`.
2. **`frontend-tests`**: Runs ESLint, executes `npm test`, and validates production Next.js builds (`npm run build`).
3. **`docker-build-check`**: Builds all container images to ensure Dockerfiles remain valid.

For an in-depth reference on pipeline stages and configuration, see [CI/CD Pipeline](../04-reference/ci-cd-pipeline.md).