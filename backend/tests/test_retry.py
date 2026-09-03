import uuid
from fastapi.testclient import TestClient
import httpx
from sqlalchemy.orm import Session

from app.models.dead_letter import DeadLetterTask
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.workflow import Workflow


def test_task_recovers_after_retry_and_completes_job(client: TestClient, member_token: str, mock_http):
    """Verifies a flaky task retries upon transient failure and eventually succeeds, completing the job."""
    # Flaky endpoint: first request fails with 500, second request succeeds with 200
    mock_http.get("https://flaky-service.internal/process").side_effect = [
        httpx.Response(500, json={"error": "Internal Server Error"}),
        httpx.Response(200, json={"result": "Success on retry"}),
    ]

    wf_payload = {
        "name": "Flaky Recovery Workflow",
        "definition": [
            {
                "name": "Flaky Task",
                "type": "http_call",
                "config": {
                    "url": "https://flaky-service.internal/process",
                    "method": "GET",
                },
                "max_retries": 2,
            }
        ],
    }
    wf_res = client.post("/workflows", json=wf_payload, headers={"Authorization": f"Bearer {member_token}"})
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    job_res = client.post(f"/workflows/{wf_id}/jobs", headers={"Authorization": f"Bearer {member_token}"})
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Trigger job in eager Celery mode (runs attempt 1 -> catches 500 -> schedules retry -> attempt 2 succeeds)
    trigger_res = client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {member_token}"})
    assert trigger_res.status_code == 200

    # Verify task recovered and job completed
    get_job = client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {member_token}"})
    final_job = get_job.json()
    assert final_job["status"] == JobStatus.COMPLETED.value

    task = final_job["tasks"][0]
    assert task["status"] == TaskStatus.COMPLETED.value
    assert task["retry_count"] == 1
    assert task["output_data"]["status_code"] == 200
    assert "Success on retry" in task["output_data"]["body"]


def test_task_exhausts_retries_and_dead_letters(client: TestClient, member_token: str, admin_token: str, mock_http, db_session: Session):
    """Verifies persistent failure exhausts retries, marks job failed, and creates a dead-letter record."""
    # Persistent failure endpoint
    mock_http.get("https://unreachable.internal/fail").respond(status_code=502, text="Bad Gateway")

    wf_payload = {
        "name": "Failing Workflow",
        "definition": [
            {
                "name": "Fatal Step",
                "type": "http_call",
                "config": {
                    "url": "https://unreachable.internal/fail",
                    "method": "GET",
                },
                "max_retries": 2,
            }
        ],
    }
    wf_res = client.post("/workflows", json=wf_payload, headers={"Authorization": f"Bearer {member_token}"})
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    job_res = client.post(f"/workflows/{wf_id}/jobs", headers={"Authorization": f"Bearer {member_token}"})
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Trigger job
    client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {member_token}"})

    # Verify job failed
    get_job = client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {member_token}"})
    failed_job = get_job.json()
    assert failed_job["status"] == JobStatus.FAILED.value

    task_data = failed_job["tasks"][0]
    assert task_data["status"] == TaskStatus.FAILED.value
    assert task_data["retry_count"] == 2
    assert "Bad Gateway" in task_data["error_message"] or "502" in task_data["error_message"]

    # Query dead-letter endpoint as admin
    dl_res = client.get("/dead-letters", headers={"Authorization": f"Bearer {admin_token}"})
    assert dl_res.status_code == 200
    dead_letters = dl_res.json()
    assert len(dead_letters) >= 1

    matched = next((dl for dl in dead_letters if dl["job_id"] == job_id), None)
    assert matched is not None
    assert matched["task_type"] == "http_call"
    assert matched["retry_count"] == 2
    assert matched["requeued_at"] is None
    assert matched["error_message"] is not None


def test_dead_letter_requeue_and_successful_retry(client: TestClient, member_token: str, admin_token: str, mock_http, db_session: Session):
    """Verifies that requeueing a dead-letter task resets state and allows execution to succeed on retry."""
    # Initially failing endpoint
    mock_http.get("https://service.recovery.internal/action").respond(status_code=500, text="Temporary Crash")

    wf_payload = {
        "name": "Requeue Recovery WF",
        "definition": [
            {
                "name": "Recoverable Task",
                "type": "http_call",
                "config": {
                    "url": "https://service.recovery.internal/action",
                    "method": "GET",
                },
                "max_retries": 1,
            }
        ],
    }
    wf_res = client.post("/workflows", json=wf_payload, headers={"Authorization": f"Bearer {member_token}"})
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    job_res = client.post(f"/workflows/{wf_id}/jobs", headers={"Authorization": f"Bearer {member_token}"})
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Trigger job -> fails into dead-letter
    client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {member_token}"})

    dl_list = client.get("/dead-letters", headers={"Authorization": f"Bearer {admin_token}"}).json()
    dl_record = next(dl for dl in dl_list if dl["job_id"] == job_id)
    dl_id = dl_record["id"]

    # Fix external service: mock now responds 200 OK
    mock_http.get("https://service.recovery.internal/action").respond(status_code=200, json={"repaired": True})

    # Admin calls requeue
    requeue_res = client.post(f"/dead-letters/{dl_id}/requeue", headers={"Authorization": f"Bearer {admin_token}"})
    assert requeue_res.status_code == 200
    requeued_data = requeue_res.json()
    assert requeued_data["requeued_at"] is not None

    # In eager mode, requeue dispatched execute_task immediately, which now succeeds
    check_job = client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {member_token}"}).json()
    assert check_job["status"] == JobStatus.COMPLETED.value
    task = check_job["tasks"][0]
    assert task["status"] == TaskStatus.COMPLETED.value
    assert "repaired" in task["output_data"]["body"]
