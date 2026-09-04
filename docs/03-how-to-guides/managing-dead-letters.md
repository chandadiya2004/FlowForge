# Managing Dead Letters

In distributed workflow systems, tasks can fail permanently due to invalid input data, unhandled business logic bugs, or persistent external service outages. Rather than dropping failed tasks or letting them block worker queues, FlowForge routes exhausted tasks into a **Dead-Letter Queue (DLQ)**.

This guide explains how to inspect dead-lettered tasks via the dashboard and API, how to diagnose root causes using failure snapshots, and how to safely requeue tasks once issues are resolved.

---

## What Triggers a Dead Letter?

A task is transitioned into the Dead-Letter table (`dead_letter_tasks`) only after it has:
1. Attempted execution and encountered an unhandled exception or non-2xx HTTP response.
2. Undergone all configured retry attempts with exponential backoff (`retry_count >= max_retries`).
3. Been marked as permanently `failed` by the worker, causing the parent `Job` to halt.

---

## 1. Viewing Dead Letters via the Dashboard

Inspecting and requeuing dead letters requires an account with the **`admin`** role.

1. Log into the FlowForge dashboard at `http://localhost:3000`.
2. Click **"Dead Letters"** in the top navigation bar, or visit:
   ```
   http://localhost:3000/dead-letters
   ```
3. If your account has the `admin` role, you will see a table listing all dead-lettered tasks ordered by failure time (`failed_at DESC`).
4. If your account is a standard `member`, the page displays an **"Access Denied"** warning. (To elevate your role for local testing, see [First Workflow Walkthrough](../02-tutorials/first-workflow-walkthrough.md#2-elevate-your-account-to-admin-for-dead-letter-access)).

---

## 2. Viewing Dead Letters via the REST API

Administrators can query dead-letter endpoints programmatically:

### List All Dead Letters
```bash
curl -X GET "http://localhost:8000/dead-letters" \
  -H "Authorization: Bearer <ADMIN_JWT_ACCESS_TOKEN>"
```

#### Filtering by Workflow
To view dead letters associated with a specific pipeline:
```bash
curl -X GET "http://localhost:8000/dead-letters?workflow_id=<WORKFLOW_UUID>" \
  -H "Authorization: Bearer <ADMIN_JWT_ACCESS_TOKEN>"
```

### Fetch a Specific Dead Letter Record
```bash
curl -X GET "http://localhost:8000/dead-letters/<DEAD_LETTER_UUID>" \
  -H "Authorization: Bearer <ADMIN_JWT_ACCESS_TOKEN>"
```

---

## 3. Diagnosing Failures from the Record Snapshot

Each dead-letter entry captures an immutable snapshot of the failure context. Here is an example API response:

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
  "failed_at": "2026-09-04T10:15:30.123456Z",
  "requeued_at": null
}
```

### Key Diagnostic Fields

| Field | Purpose & Diagnostic Value |
| :--- | :--- |
| **`task_type`** | Identifies which execution handler ran (`http_call`, `log_message`, `sleep`). Directs you to the relevant worker code (`worker/tasks/registry.py`). |
| **`error_message`** | The raw string representation of the exception. For network calls, this contains HTTP status codes (e.g. `404 Not Found`, `503 Service Unavailable`, `ConnectTimeout`). |
| **`input_data`** | The exact parameters supplied to the task. Use this to verify if the URL was misspelled, an authentication header was missing, or a required parameter was omitted. |
| **`retry_count`** | Confirms how many retry attempts were executed before abandonment. |
| **`failed_at`** | Pinpoints the timestamp of permanent failure for cross-referencing worker container logs. |

---

## 4. Requeueing Dead-Lettered Tasks

Once the underlying issue is resolved (e.g. the downstream service recovered, or a firewall rule was updated), administrators can re-drive the failed task.

### Requeue via Dashboard
In the `/dead-letters` view, click the **"Requeue"** button in the row corresponding to the task. A green confirmation banner will appear.

### Requeue via API
```bash
curl -X POST "http://localhost:8000/dead-letters/<DEAD_LETTER_UUID>/requeue" \
  -H "Authorization: Bearer <ADMIN_JWT_ACCESS_TOKEN>"
```

### What Happens Behind the Scenes During Requeue:

1. **State Reset**: The original `Task` row in PostgreSQL is reset:
   - `status` reverts to `"pending"`.
   - `retry_count` resets to `0`.
   - `error_message` is cleared.
2. **Job Reopening**: If the parent `Job` was marked `failed`, its status is updated back to `"running"`, and `completed_at` is cleared.
3. **Audit Trail Preservation**: The `DeadLetterTask` record is **not deleted**. Instead, its `requeued_at` column is stamped with the current UTC timestamp. This provides an audit log showing that the failure occurred and was operator-requeued.
4. **Celery Re-Dispatch**: The task is published fresh to Celery using its original priority queue (`high`, `default`, or `low`), allowing execution to resume immediately.