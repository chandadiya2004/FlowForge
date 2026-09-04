# API Reference

> [!NOTE]
> This is a scannable index. The canonical, always-current schema is FastAPI's auto-generated interactive documentation at **`http://localhost:8000/docs` (Swagger UI)** and **`http://localhost:8000/redoc`**—use those for exact request/response shapes and to try endpoints live.

---

## Overview & Authentication Schemes

FlowForge exposes a RESTful JSON API. All endpoints (except public authentication and health probes) require a valid JWT Access Token passed in the HTTP Authorization header:

```http
Authorization: Bearer <access_token>
```

### Authorization Levels
- **None (Public)**: Accessible without authentication.
- **Any Authenticated User**: Any user presenting a valid, non-expired access token.
- **Owner or Admin**: The user who owns the target resource (workflow or job), or any user with the `admin` role.
- **Admin Only**: Restricted strictly to users whose token carries the `role: "admin"` claim.

---

## 1. Authentication Endpoints (`/auth`)

| Method | Endpoint | Authorization | Description | Key Request Fields | Key Response Fields |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | None (Public) | Registers a new user account. Defaults role to `member`. | `email`, `password` | `id`, `email`, `role`, `created_at` |
| `POST` | `/auth/login` | None (Public) | Authenticates with email and password, returning tokens. | `email`, `password` | `access_token`, `refresh_token`, `token_type`, `expires_in` |
| `POST` | `/auth/refresh` | None (Public) | Rotates and issues a new access token using a valid refresh token. | `refresh_token` | `access_token`, `refresh_token`, `token_type`, `expires_in` |
| `GET` | `/auth/me` | Any Authenticated | Retrieves identity and role details for the currently logged-in user. | *(None)* | `id`, `email`, `role`, `is_active`, `created_at` |

---

## 2. Workflow Endpoints (`/workflows`)

| Method | Endpoint | Authorization | Description | Key Request Fields | Key Response Fields |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/workflows` | Any Authenticated | Creates a new workflow definition owned by the caller. | `name`, `description` *(opt)*, `definition` *(array of step objects)* | `id`, `name`, `description`, `owner_id`, `definition`, `is_active`, `created_at` |
| `GET` | `/workflows` | Any Authenticated | Lists workflows. Members see only their own; admins see all. Filterable via `?include_inactive=false`. | `include_inactive` *(query param, default: false)* | Array of Workflow objects |
| `GET` | `/workflows/{workflow_id}` | Owner or Admin | Retrieves full details of a specific workflow. | `workflow_id` *(path)* | Workflow object |
| `PUT` | `/workflows/{workflow_id}` | Owner or Admin | Updates workflow name, description, or step definition. | `name` *(opt)*, `description` *(opt)*, `definition` *(opt)* | Updated Workflow object |
| `DELETE` | `/workflows/{workflow_id}` | Owner or Admin | Soft-deletes a workflow by marking `is_active = False`. | `workflow_id` *(path)* | `{"message": "Workflow deactivated successfully"}` |
| `POST` | `/workflows/{workflow_id}/jobs` | Owner or Admin | Instantiates a new `Job` in `pending` status and unpacks definition into sequential `Task` records. | `priority` *(body, int 1-10, default: 5)* | Job detail object with nested `tasks` array |

---

## 3. Job & Task Endpoints (`/jobs`)

| Method | Endpoint | Authorization | Description | Key Request Fields | Key Response Fields |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/jobs` | Any Authenticated | Lists jobs ordered by creation date descending. Filterable via `?status=<status>`. | `status` *(query param, opt)* | Array of Job summary objects (`id`, `workflow_id`, `status`, `priority`, timestamps) |
| `GET` | `/jobs/{job_id}` | Owner or Admin | Retrieves comprehensive job details including nested, sequence-ordered child tasks. | `job_id` *(path)* | Job detail object with full nested `tasks` array |
| `POST` | `/jobs/{job_id}/trigger` | Owner or Admin | Triggers execution of a `pending` job. Dispatches the first task to Celery via Redis using priority queueing. | `job_id` *(path)* | Job detail object |
| `PUT` | `/jobs/{job_id}/priority` | Owner or Admin | Updates the numeric priority (1–10) of a job while it remains in `pending` status. | `priority` *(body, int 1-10)* | Updated Job summary object |
| `GET` | `/jobs/{job_id}/tasks` | Owner or Admin | Retrieves the ordered task list for a job without full job metadata. | `job_id` *(path)* | Array of Task objects (`id`, `name`, `type`, `sequence`, `status`, `input_data`, `output_data`, `retry_count`) |

---

## 4. Dead-Letter Endpoints (`/dead-letters`)

| Method | Endpoint | Authorization | Description | Key Request Fields | Key Response Fields |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/dead-letters` | Admin Only | Lists all permanently failed tasks. Supports optional filtering by workflow. | `workflow_id` *(query param, opt)* | Array of DeadLetterTask objects ordered by `failed_at DESC` |
| `GET` | `/dead-letters/{dead_letter_id}` | Admin Only | Retrieves complete diagnostic snapshot of a specific dead-letter record. | `dead_letter_id` *(path)* | DeadLetterTask object (`id`, `task_id`, `job_id`, `task_type`, `input_data`, `error_message`, `retry_count`, `failed_at`, `requeued_at`) |
| `POST` | `/dead-letters/{dead_letter_id}/requeue` | Admin Only | Resets original task, reopens parent job, stamps `requeued_at`, and dispatches execution fresh to Celery. | `dead_letter_id` *(path)* | Updated DeadLetterTask object with `requeued_at` timestamp |

---

## 5. System & Health Endpoints

| Method | Endpoint | Authorization | Description | Key Request Fields | Key Response Fields |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/health` | None (Public) | Liveness probe endpoint returning service status. Used by Docker & monitoring agents. | *(None)* | `{"status": "ok"}` |
| `GET` | `/admin-check` | Admin Only | Verification endpoint confirming token carries valid `admin` role privileges. | *(None)* | `{"status": "ok", "message": "Admin access granted", "role": "admin"}` |
| `POST` | `/system/ping-worker` | None (Debug) | Publishes a throwaway `ping` verification task to Celery via Redis broker. | *(None)* | `{"task_id": "<uuid>", "status": "dispatched"}` |
| `GET` | `/system/task-result/{task_id}` | None (Debug) | Inspects task status directly from Celery Redis result backend (`PENDING`, `SUCCESS`, etc.). | `task_id` *(path)* | `{"task_id": "<uuid>", "status": "SUCCESS", "result": ...}` |