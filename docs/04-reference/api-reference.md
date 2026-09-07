# FlowForge REST API Reference

FlowForge provides an enterprise-grade, RESTful HTTP API for workflow management, job dispatching, real-time status tracking, and dead-letter queue operations. This document provides an exhaustive technical specification of all available endpoints, authentication requirements, request/response schemas, status codes, and error models.

> [!NOTE]
> The canonical, interactive OpenAPI specification is served live by FastAPI at **`http://localhost:8000/docs` (Swagger UI)** and **`http://localhost:8000/redoc` (ReDoc)**. Use those interfaces to inspect real-time schemas and execute test requests directly against your local container cluster.

---

## API Protocol & Architectural Standards

### Base URL Conventions
- **Local Development**: `http://localhost:8000` (or `http://127.0.0.1:8000`)
- **Docker Internal Bridge**: `http://backend:8000`
- **Media Type**: All requests and responses use `application/json; charset=utf-8` unless otherwise stated.

### Authentication & Token Flow
Except for public authentication (`/auth/register`, `/auth/login`, `/auth/refresh`) and health probes (`/health`), all endpoints require a cryptographically signed JWT access token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

Tokens are generated using HMAC-SHA256 (`HS256`) via `python-jose`, embedding user identity (`sub`) and role (`role`). Tokens default to a 60-minute expiration window governed by `JWT_EXPIRE_MINUTES`.

### Role-Based Access Control (RBAC) Permissions
- **Public**: Accessible without an Authorization header.
- **Authenticated (`member`, `admin`)**: Any user with a valid, unexpired access token. Regular members only query and mutate resources they own.
- **Owner or Admin**: The specific user who authored the workflow or triggered the job, or any user possessing the `admin` role.
- **Admin Only**: Restricted strictly to users whose JWT claims verify `role: "admin"` via the `require_role("admin")` dependency guard.

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
    classDef client fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;
    classDef auth fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e0e7ff;
    classDef rbac fill:#581c87,stroke:#c084fc,stroke-width:2px,color:#faf5ff;
    classDef route fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#ecfdf5;
    classDef error fill:#7f1d1d,stroke:#f87171,stroke-width:2px,color:#fef2f2;

    Req([Incoming HTTP Request]):::client --> RouteType{Route Requires Auth?}:::auth

    RouteType -->|No: /auth/* or /health| PublicRoute[Execute Public Controller]:::route
    RouteType -->|Yes: /workflows, /jobs, /dead-letters| BearerCheck{Authorization: Bearer Present?}:::auth

    BearerCheck -->|Missing / Malformed| Err401["HTTP 401 Unauthorized\n(WWW-Authenticate: Bearer)"]:::error
    BearerCheck -->|Present| VerifyJWT[Verify JWT Signature & Expiration\n(python-jose & JWT_SECRET)]:::auth

    VerifyJWT -->|Signature Invalid / Expired| Err401
    VerifyJWT -->|Valid| LoadUser[Load User from DB\n(Verify is_active == True)]:::auth

    LoadUser -->|Inactive User| Err401
    LoadUser --> RBACCheck{Route RBAC Permission Gate}:::rbac

    RBACCheck -->|Admin Only: require_role('admin')| AdminGate{User Role == 'admin'?}:::rbac
    AdminGate -->|No| Err403["HTTP 403 Forbidden\n(Admin privilege required)"]:::error
    AdminGate -->|Yes| ExecRoute[Execute Controller & DB Transaction]:::route

    RBACCheck -->|Owner or Admin| OwnerGate{User == Owner OR Role == 'admin'?}:::rbac
    OwnerGate -->|No| Err403
    OwnerGate -->|Yes| ExecRoute

    RBACCheck -->|Any Authenticated| ExecRoute
    ExecRoute --> Resp([JSON HTTP Response]):::client
```

### Standard Error Schema
All error responses return a standardized JSON structure with appropriate HTTP status codes:

```json
{
  "detail": "Descriptive error message explaining the failure condition."
}
```

| HTTP Status | Meaning | Typical Trigger |
| :--- | :--- | :--- |
| **`400 Bad Request`** | Validation failure | Missing required body fields, invalid JSON, or workflow is deactivated. |
| **`401 Unauthorized`** | Authentication failure | Missing, malformed, or expired JWT bearer token. |
| **`403 Forbidden`** | Authorization rejection | Insufficient permissions (e.g. standard member accessing `/dead-letters`). |
| **`404 Not Found`** | Resource missing | Requested workflow UUID, job UUID, or task UUID does not exist. |
| **`409 Conflict`** | State conflict | Duplicate user email, or triggering a job not in `pending` status. |

---

## 1. Authentication Endpoints (`/auth`)

### Register User
`POST /auth/register`
Creates a new user account with hashed credentials. Defaults the user role to `member`.

- **Authorization**: Public
- **Request Body**:
  ```json
  {
    "email": "developer@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Responses**:
  - `201 Created`:
    ```json
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "email": "developer@example.com",
      "role": "member",
      "is_active": true,
      "created_at": "2026-09-07T10:00:00.000000Z"
    }
    ```
  - `409 Conflict`: Returned if the email address is already registered.

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "developer@example.com", "password": "SecurePassword123!"}'
```

---

### User Login
`POST /auth/login`
Authenticates credentials and returns a short-lived access token and a long-lived refresh token.

- **Authorization**: Public
- **Request Body**:
  ```json
  {
    "email": "developer@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Responses**:
  - `200 OK`:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```
  - `401 Unauthorized`: Incorrect email or password.

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "developer@example.com", "password": "SecurePassword123!"}'
```

---

### Refresh Access Token
`POST /auth/refresh`
Exchanges a valid refresh token for a newly signed access token without requiring re-authentication.

- **Authorization**: Public
- **Request Body**:
  ```json
  {
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
  ```
- **Responses**:
  - `200 OK`: Returns new `access_token` with original `refresh_token`.
  - `401 Unauthorized`: Invalid or expired refresh token.

```bash
curl -X POST "http://localhost:8000/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<YOUR_REFRESH_TOKEN>"}'
```

---

### Get Current User Profile
`GET /auth/me`
Retrieves identity and role information for the currently authenticated caller.

- **Authorization**: Any Authenticated User
- **Responses**:
  - `200 OK`:
    ```json
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "email": "developer@example.com",
      "role": "admin",
      "is_active": true,
      "created_at": "2026-09-07T10:00:00.000000Z"
    }
    ```

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## 2. Workflow Management Endpoints (`/workflows`)

### Create Workflow
`POST /workflows`
Creates a declarative workflow definition consisting of ordered task steps.

- **Authorization**: Any Authenticated User
- **Request Body**:
  ```json
  {
    "name": "Data Sync Pipeline",
    "description": "Nightly batch synchronization with CRM",
    "definition": [
      {
        "name": "Step 1: Init",
        "type": "log_message",
        "config": { "message": "Sync started" },
        "max_retries": 3
      },
      {
        "name": "Step 2: Sync Webhook",
        "type": "http_call",
        "config": {
          "url": "https://api.example.com/sync",
          "method": "POST",
          "timeout": 10.0
        },
        "max_retries": 2
      }
    ]
  }
  ```
- **Responses**:
  - `201 Created`: Returns the newly persisted Workflow object with generated UUID and `is_active: true`.

```bash
curl -X POST "http://localhost:8000/workflows" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Data Sync Pipeline",
    "description": "Nightly batch synchronization",
    "definition": [
      {
        "name": "Init",
        "type": "log_message",
        "config": {"message": "Starting"},
        "max_retries": 3
      }
    ]
  }'
```

---

### List Workflows
`GET /workflows`
Retrieves workflows. Regular users only see workflows they own; administrators receive all workflows across the platform.

- **Authorization**: Any Authenticated User
- **Query Parameters**:
  - `include_inactive` *(boolean, default: `false`)*: Include soft-deleted workflows.
- **Responses**:
  - `200 OK`: Array of Workflow objects ordered by `created_at DESC`.

```bash
curl -X GET "http://localhost:8000/workflows?include_inactive=false" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

### Get Workflow Detail
`GET /workflows/{workflow_id}`
Retrieves complete metadata and step definition array for a specific workflow.

- **Authorization**: Owner or Admin
- **Path Parameters**:
  - `workflow_id` *(UUID, required)*
- **Responses**:
  - `200 OK`: Workflow object.
  - `403 Forbidden`: Caller does not own the workflow and is not an admin.
  - `404 Not Found`: Workflow does not exist.

```bash
curl -X GET "http://localhost:8000/workflows/<WORKFLOW_UUID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

### Update Workflow
`PUT /workflows/{workflow_id}`
Modifies workflow metadata or updates the task step configuration array.

- **Authorization**: Owner or Admin
- **Request Body**: Accepts partial updates (`name`, `description`, `definition`).
- **Responses**:
  - `200 OK`: Updated Workflow object.

```bash
curl -X PUT "http://localhost:8000/workflows/<WORKFLOW_UUID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Data Sync Pipeline"}'
```

---

### Soft-Delete Workflow
`DELETE /workflows/{workflow_id}`
Deactivates a workflow by setting `is_active = False`. Existing job records remain preserved.

- **Authorization**: Owner or Admin
- **Responses**:
  - `200 OK`: `{"status": "ok", "message": "Workflow deactivated successfully."}`

```bash
curl -X DELETE "http://localhost:8000/workflows/<WORKFLOW_UUID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

### Instantiate Job from Workflow
`POST /workflows/{workflow_id}/jobs`
Instantiates a new execution `Job` in `pending` status and unpacks the workflow's JSON definition into ordered [Task](file:///d:/Edutation(P)/FlowForge/backend/app/models/task.py) records.

- **Authorization**: Owner or Admin
- **Request Body** *(Optional)*:
  ```json
  {
    "priority": 2
  }
  ```
- **Responses**:
  - `201 Created`: Returns Job detail object with populated `tasks` array.
  - `400 Bad Request`: Cannot create a job from a deactivated (`is_active == false`) workflow.

```bash
curl -X POST "http://localhost:8000/workflows/<WORKFLOW_UUID>/jobs" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"priority": 2}'
```

---

## 3. Job & Task Endpoints (`/jobs`)

### List Jobs
`GET /jobs`
Lists execution jobs. Regular members see jobs they triggered; administrators see all platform executions.

- **Authorization**: Any Authenticated User
- **Query Parameters**:
  - `status` *(string, optional)*: Filter by job state (`pending`, `running`, `completed`, `failed`, `cancelled`).
- **Responses**:
  - `200 OK`: Array of Job summary objects ordered by `created_at DESC`.

```bash
curl -X GET "http://localhost:8000/jobs?status=running" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

### Get Job Details with Nested Tasks
`GET /jobs/{job_id}`
Retrieves comprehensive job metadata including its sequence-ordered array of child tasks. Used by the Next.js frontend polling loop.

- **Authorization**: Owner or Admin
- **Responses**:
  - `200 OK`:
    ```json
    {
      "id": "e4f5a6b7-c8d9-0123-4567-89abcdef0123",
      "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "triggered_by": "11223344-5566-7788-99aa-bbccddeeff00",
      "status": "running",
      "priority": 2,
      "started_at": "2026-09-07T10:05:00.000000Z",
      "completed_at": null,
      "created_at": "2026-09-07T10:04:55.000000Z",
      "tasks": [
        {
          "id": "b1c2d3e4-f5a6-7890-1234-567890abcdef",
          "job_id": "e4f5a6b7-c8d9-0123-4567-89abcdef0123",
          "name": "Step 1: Init",
          "type": "log_message",
          "sequence": 1,
          "status": "completed",
          "retry_count": 0,
          "max_retries": 3,
          "input_data": { "message": "Sync started" },
          "output_data": { "logged": "Sync started" },
          "error_message": null,
          "started_at": "2026-09-07T10:05:00.100000Z",
          "completed_at": "2026-09-07T10:05:00.120000Z"
        }
      ]
    }
    ```

```bash
curl -X GET "http://localhost:8000/jobs/<JOB_UUID>" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

### Trigger Job Execution
`POST /jobs/{job_id}/trigger`
Triggers execution of a `pending` job. Validates that the job is pending, queries the first sequential task (`sequence == 1`), routes priority to the corresponding Redis queue (`high`, `default`, `low`), and dispatches execution to Celery.

- **Authorization**: Owner or Admin
- **Responses**:
  - `200 OK`: Job detail object confirming dispatch.
  - `400 Bad Request`: Job contains no task steps to execute.
  - `409 Conflict`: Job status is not `pending` (already running, completed, or cancelled).

```bash
curl -X POST "http://localhost:8000/jobs/<JOB_UUID>/trigger" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

### Update Job Priority
`PUT /jobs/{job_id}/priority`
Updates the execution priority of a job while it is still waiting in `pending` status.

- **Authorization**: Owner or Admin
- **Request Body**:
  ```json
  {
    "priority": 1
  }
  ```
- **Responses**:
  - `200 OK`: Updated Job summary object.
  - `409 Conflict`: Job has already transitioned out of `pending` status.

```bash
curl -X PUT "http://localhost:8000/jobs/<JOB_UUID>/priority" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"priority": 1}'
```

---

### List Tasks for a Job
`GET /jobs/{job_id}/tasks`
Retrieves lightweight list of tasks for a job without top-level job metadata.

- **Authorization**: Owner or Admin
- **Responses**:
  - `200 OK`: Array of Task objects ordered by `sequence ASC`.

```bash
curl -X GET "http://localhost:8000/jobs/<JOB_UUID>/tasks" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

---

## 4. Dead-Letter Queue Endpoints (`/dead-letters`)

### List Quarantined Tasks
`GET /dead-letters`
Retrieves all permanently failed tasks quarantined in `dead_letter_tasks`.

- **Authorization**: Admin Only (`require_role("admin")`)
- **Query Parameters**:
  - `workflow_id` *(UUID, optional)*: Filter failures originating from a specific workflow.
- **Responses**:
  - `200 OK`: Array of DeadLetterTask objects ordered by `failed_at DESC`.
  - `403 Forbidden`: Non-admin caller.

```bash
curl -X GET "http://localhost:8000/dead-letters" \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

---

### Get Dead-Letter Snapshot Detail
`GET /dead-letters/{dead_letter_id}`
Retrieves complete failure diagnostics, error trace, and input payload for a specific quarantined task.

- **Authorization**: Admin Only
- **Responses**:
  - `200 OK`:
    ```json
    {
      "id": "7b8f9e0a-1234-4567-89ab-cdef01234567",
      "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "job_id": "f0e1d2c3-b4a5-6789-0123-456789abcdef",
      "workflow_id": "3c4d5e6f-7a8b-9012-3456-789abcdef012",
      "task_type": "http_call",
      "input_data": {
        "url": "https://api.partner.example.com/v1/webhook",
        "method": "POST",
        "timeout": 10.0
      },
      "error_message": "HTTPStatusError: 503 Service Unavailable for url 'https://api.partner.example.com/v1/webhook'",
      "retry_count": 3,
      "failed_at": "2026-09-07T10:15:30.123456Z",
      "requeued_at": null
    }
    ```
  - `404 Not Found`: Dead-letter UUID does not exist.

```bash
curl -X GET "http://localhost:8000/dead-letters/<DEAD_LETTER_UUID>" \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

---

### Requeue Quarantined Task
`POST /dead-letters/{dead_letter_id}/requeue`
Resets the original task state to `pending`, reopens the parent job to `running`, stamps `requeued_at = NOW()`, and dispatches the task fresh to Celery using its original priority queue.

- **Authorization**: Admin Only
- **Responses**:
  - `200 OK`: Returns updated DeadLetterTask record showing `requeued_at` timestamp.
  - `404 Not Found`: Dead-letter record or associated task row missing.

```bash
curl -X POST "http://localhost:8000/dead-letters/<DEAD_LETTER_UUID>/requeue" \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

---

## 5. System, Health & Diagnostic Endpoints

### Platform Health Check
`GET /health`
Liveness probe returning HTTP status. Used by Docker Compose and container orchestrators.

- **Authorization**: Public
- **Responses**:
  - `200 OK`: `{"status": "ok"}`

```bash
curl -X GET "http://localhost:8000/health"
```

---

### RBAC Privilege Verification (Admin Check)
`GET /admin-check`
Confirms caller's access token carries valid administrative claims.

- **Authorization**: Admin Only (`require_role("admin")`)
- **Responses**:
  - `200 OK`:
    ```json
    {
      "status": "ok",
      "message": "Admin access granted",
      "user_id": "11223344-5566-7788-99aa-bbccddeeff00",
      "email": "admin@example.com",
      "role": "admin"
    }
    ```
  - `403 Forbidden`: Caller lacks administrator role.

```bash
curl -X GET "http://localhost:8000/admin-check" \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>"
```

---

### Celery Ping Probe (Debug)
`POST /system/ping-worker`
Dispatches a throwaway `ping` task to Celery via Redis to verify broker connectivity.

- **Authorization**: Public (Debug)
- **Responses**:
  - `202 Accepted`: `{"task_id": "c4d5e6f7-...", "status": "dispatched"}`

```bash
curl -X POST "http://localhost:8000/system/ping-worker"
```

---

### Celery Task Result Probe (Debug)
`GET /system/task-result/{task_id}`
Directly queries Celery's Redis result backend to inspect execution state (`PENDING`, `SUCCESS`, `FAILURE`).

- **Authorization**: Public (Debug)
- **Responses**:
  - `200 OK`: `{"task_id": "...", "status": "SUCCESS", "result": "pong"}`

```bash
curl -X GET "http://localhost:8000/system/task-result/<CELERY_TASK_ID>"
```

---

## Related Documentation & Next Steps

- [Relational Data Model Specification](data-model.md) — Comprehensive PostgreSQL schema, table layouts, and JSONB definitions.
- [Environment Variables Reference](environment-variables.md) — Configuration guide for all platform environment variables.
- [Managing Dead Letters Guide](../03-how-to-guides/managing-dead-letters.md) — Operational walkthrough for handling quarantined tasks.
- [Platform Overview](../01-introduction/overview.md) — Architectural philosophy and system capabilities.
- [Architecture Diagram & Network Topology](../01-introduction/architecture-diagram.md) — Container networking and protocol boundaries.