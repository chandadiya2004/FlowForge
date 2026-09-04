# First Workflow Walkthrough

This tutorial guides you through creating, triggering, and inspecting your first automated pipeline in FlowForge. You will start with a fresh user account, author a multi-step workflow featuring automatic retry and failure handling, trigger execution with priority routing, monitor live status transitions in the dashboard, and inspect the resulting dead-letter record.

---

## 1. Create an Account and Log In

FlowForge enforces JWT-based authentication and role-based access control (RBAC).

1. Ensure the platform is running (see [Getting Started](getting-started.md)).
2. Open your browser and navigate to the registration page:
   ```
   http://localhost:3000/register
   ```
3. Register a new user account:
   - **Email**: `operator@example.com`
   - **Password**: `SecurePass123!`
4. Upon registration, you are redirected to `/login`. Sign in with your credentials.
5. You will land on the **Workflows** page (`http://localhost:3000/workflows`).

---

## 2. Elevate Your Account to Admin (For Dead-Letter Access)

By default, self-registered accounts are assigned the `member` role. In FlowForge, viewing and requeuing dead-lettered tasks is an administrative operation protected by `require_role("admin")`.

To grant your account administrator privileges, run this single command in your terminal while Docker Compose is running:

```bash
docker compose -f infrastructure/docker-compose.yml exec postgres \
  psql -U postgres -d flowforge -c "UPDATE users SET role = 'admin' WHERE email = 'operator@example.com';"
```

> [!NOTE]
> After updating the role in PostgreSQL, log out from the dashboard and log back in so your browser receives a fresh JWT access token containing the updated `"role": "admin"` claim.

---

## 3. Create a Multi-Step Workflow

1. On the **Workflows** page (`http://localhost:3000/workflows`), click **"Create Workflow"**.
2. Fill out the workflow metadata:
   - **Name**: `Resilience Demo Pipeline`
   - **Description**: `Multi-step pipeline demonstrating sequential execution, retries, and dead-letter capture.`
3. In the **Definition (JSON)** field, paste the following 3-step workflow configuration:

```json
[
  {
    "name": "Step 1 - Pipeline Initialization",
    "type": "log_message",
    "config": {
      "message": "Initiating batch data synchronization..."
    },
    "max_retries": 3
  },
  {
    "name": "Step 2 - Simulated Delay",
    "type": "sleep",
    "config": {
      "seconds": 3
    },
    "max_retries": 3
  },
  {
    "name": "Step 3 - Remote Sync Webhook",
    "type": "http_call",
    "config": {
      "url": "https://httpbin.org/status/500",
      "method": "GET",
      "timeout": 5.0
    },
    "max_retries": 2
  }
]
```

### Understanding This Definition
- **Step 1 (`log_message`)**: Runs instantly and logs a message to the worker console.
- **Step 2 (`sleep`)**: Pauses the worker for 3 seconds, giving you time to observe the live `running` state in the dashboard.
- **Step 3 (`http_call`)**: Sends an HTTP request to `https://httpbin.org/status/500`, which deliberately returns an HTTP 500 error. With `max_retries: 2`, this step is designed to fail twice, demonstrate exponential backoff, and ultimately route to the dead-letter queue.

4. Click **"Create Workflow"**. The new workflow appears immediately in your list.

---

## 4. Set Priority and Trigger the Job

1. Click on **"Resilience Demo Pipeline"** in the list to open the workflow detail page (`http://localhost:3000/workflows/<workflow-id>`).
2. Locate the **"Trigger Job"** control card on the right side of the screen.
3. In the **Priority (1-10)** dropdown, select **`2 - High`** (in FlowForge, lower numbers denote higher urgency: 1–3 routes to the `high` queue, 4–7 to `default`, and 8–10 to `low`).
4. Click the **"Trigger Job"** button.

---

## 5. Observe Live Execution in the Dashboard

Upon triggering, the dashboard navigates automatically to the Job Detail view (`http://localhost:3000/jobs/<job-id>`). The page automatically polls the backend every 2 seconds.

Here is what happens step by step:

### Stage 1: Dispatched (`pending` $\rightarrow$ `running`)
- The job initially displays a yellow `pending` badge.
- Within milliseconds, the Celery worker picks up the job from the `high` Redis queue and transitions the job to blue `running`.

### Stage 2: Step 1 Completes Instantly
- **Step 1 - Pipeline Initialization**:
  - The status transitions immediately from `pending` to `running` to `completed` (green badge).
  - Click on the step row to view the output payload: `{"logged": "Initiating batch data synchronization..."}`.

### Stage 3: Step 2 Runs with Delay
- **Step 2 - Simulated Delay**:
  - Transitions to `running`. Because it executes `time.sleep(3)`, the status remains `running` for roughly 3 seconds.
  - Once finished, it transitions to `completed` with output `{"slept": 3.0}`.
  - The orchestrator automatically evaluates the sequence and dispatches Step 3.

### Stage 4: Step 3 Fails and Retries
- **Step 3 - Remote Sync Webhook**:
  - The HTTP request to `https://httpbin.org/status/500` returns an HTTP 500 Server Error.
  - The worker catches the error, updates the status to orange `retrying`, and increments `retry_count: 1/2`.
  - An exponential backoff delay is scheduled via Celery countdown without blocking other queue tasks.
  - The worker attempts execution a second time. The request fails again.
  - Since `retry_count` has reached `max_retries` (2), the worker exhausts retries.
  - Step 3 switches to red `failed` with the error message: `Server error '500 Internal Server Error' for url 'https://httpbin.org/status/500'`.
  - The parent Job status transitions to red `failed`.
  - The frontend polling loop detects the terminal `failed` state and stops polling automatically.

---

## 6. Inspect and Requeue from Dead Letters

Because Step 3 exhausted all retry attempts, FlowForge isolated the failed step into the Dead-Letter table.

1. In the top navigation bar, click **"Dead Letters"** (`http://localhost:3000/dead-letters`).
2. You will see a table displaying permanently failed tasks. Locate the record for **Step 3 - Remote Sync Webhook**:
   - **Task Type**: `http_call`
   - **Retries**: `2`
   - **Failed At**: Timestamp of permanent failure
   - **Error**: `Server error '500 Internal Server Error' for url 'https://httpbin.org/status/500'`
   - **Input Payload**: `{"url": "https://httpbin.org/status/500", "method": "GET", "timeout": 5.0}`
3. Click the **"Requeue"** button next to the dead-letter record.

### What Happens When You Requeue:
1. The backend (`POST /dead-letters/{id}/requeue`) resets the task status to `pending` and sets `retry_count = 0`.
2. The parent Job is re-opened from `failed` to `running`.
3. The dead-letter record is stamped with `requeued_at` for auditing.
4. The task is re-dispatched to the worker via Celery, giving operators a one-click mechanism to recover from transient outages after fixing root causes.

---

## What You Just Learned

Through this single workflow, you observed the full FlowForge architecture in action:

| Subsystem | What You Experienced | Codebase Location |
| :--- | :--- | :--- |
| **Authentication & RBAC** | Registered, logged in with JWT tokens, and accessed admin-only dead-letter endpoints using role claims. | `backend/app/api/auth.py`, `backend/app/core/deps.py` |
| **Workflow Definition** | Authored an ordered step list with custom task types (`log_message`, `sleep`, `http_call`) and retry budgets. | `backend/app/models/workflow.py`, `worker/tasks/registry.py` |
| **Priority Queueing** | Chose priority `2`, routing execution to Celery's `high` queue rather than `default` or `low`. | `backend/app/core/queue_routing.py` |
| **Asynchronous Orchestration** | Watched the backend return an immediate response while the worker executed steps sequentially via Celery. | `worker/tasks/execute_task.py`, `worker/tasks/orchestrate.py` |
| **Exponential Backoff Retries** | Observed automated retries with scheduled countdown delays before giving up. | `worker/tasks/execute_task.py` |
| **Dead-Letter Isolation** | Captured the exhausted task into a dedicated table preserving error diagnostics without dropping data. | `backend/app/models/dead_letter.py`, `backend/app/api/dead_letters.py` |
| **Reactive Dashboard** | Monitored real-time status transitions via lightweight client polling that terminated on completion. | `frontend/src/app/jobs/[id]/page.tsx` |