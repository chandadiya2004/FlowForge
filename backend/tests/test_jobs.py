import uuid
from fastapi.testclient import TestClient

from app.models.job import JobStatus
from app.models.task import TaskStatus


def test_create_job_unpacks_tasks_in_sequence(client: TestClient, member_token: str):
    # Create workflow with 3 steps
    wf_payload = {
        "name": "Sequential Workflow",
        "definition": [
            {"name": "Init Step", "type": "log_message", "config": {"message": "Initializing"}},
            {"name": "Process Step", "type": "sleep", "config": {"seconds": 0.1}},
            {"name": "Finalize Step", "type": "log_message", "config": {"message": "Done"}},
        ],
    }
    wf_res = client.post("/workflows", json=wf_payload, headers={"Authorization": f"Bearer {member_token}"})
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    # Create Job via POST /workflows/{wf_id}/jobs
    job_res = client.post(f"/workflows/{wf_id}/jobs", json={"priority": 4}, headers={"Authorization": f"Bearer {member_token}"})
    assert job_res.status_code == 201
    job_data = job_res.json()
    assert job_data["status"] == "pending"
    assert job_data["priority"] == 4

    # Verify tasks were unpacked in sequence order
    tasks = job_data["tasks"]
    assert len(tasks) == 3
    assert tasks[0]["sequence"] == 1
    assert tasks[0]["name"] == "Init Step"
    assert tasks[0]["status"] == "pending"

    assert tasks[1]["sequence"] == 2
    assert tasks[1]["name"] == "Process Step"
    assert tasks[1]["status"] == "pending"

    assert tasks[2]["sequence"] == 3
    assert tasks[2]["name"] == "Finalize Step"
    assert tasks[2]["status"] == "pending"


def test_trigger_job_runs_to_completion_in_eager_mode(client: TestClient, member_token: str, mock_http):
    # Mock external HTTP endpoint used by http_call task
    mock_http.get("https://api.example.com/data").respond(
        status_code=200,
        json={"greeting": "Hello, FlowForge!"},
    )

    # Create workflow with log, http_call, and sleep
    wf_payload = {
        "name": "Full Execution WF",
        "definition": [
            {"name": "Step 1: Log", "type": "log_message", "config": {"message": "Starting job..."}},
            {
                "name": "Step 2: HTTP Fetch",
                "type": "http_call",
                "config": {"url": "https://api.example.com/data", "method": "GET"},
            },
            {"name": "Step 3: Quick Sleep", "type": "sleep", "config": {"seconds": 0.05}},
        ],
    }
    wf_res = client.post("/workflows", json=wf_payload, headers={"Authorization": f"Bearer {member_token}"})
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    # Create Job
    job_res = client.post(f"/workflows/{wf_id}/jobs", json={"priority": 5}, headers={"Authorization": f"Bearer {member_token}"})
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Trigger Job (in Celery eager mode, runs synchronous cascade to completion)
    trigger_res = client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {member_token}"})
    assert trigger_res.status_code == 200

    # Fetch updated job details
    get_job = client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {member_token}"})
    assert get_job.status_code == 200
    final_job = get_job.json()

    # Verify overall Job completed
    assert final_job["status"] == JobStatus.COMPLETED.value
    assert final_job["started_at"] is not None
    assert final_job["completed_at"] is not None

    # Verify each Task completed with output
    tasks = final_job["tasks"]
    assert len(tasks) == 3
    for task in tasks:
        assert task["status"] == TaskStatus.COMPLETED.value
        assert task["completed_at"] is not None

    # Verify HTTP task captured the mocked response
    http_task = tasks[1]
    assert http_task["output_data"] is not None
    assert http_task["output_data"]["status_code"] == 200
    assert "Hello, FlowForge!" in http_task["output_data"]["body"]


def test_list_jobs_and_filter(client: TestClient, member_token: str):
    wf_res = client.post(
        "/workflows",
        json={"name": "Filter Test WF", "definition": [{"name": "Step", "type": "log_message", "config": {}}]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    client.post(f"/workflows/{wf_id}/jobs", headers={"Authorization": f"Bearer {member_token}"})

    list_res = client.get("/jobs", headers={"Authorization": f"Bearer {member_token}"})
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Filter by status=pending
    filtered_res = client.get("/jobs?status=pending", headers={"Authorization": f"Bearer {member_token}"})
    assert filtered_res.status_code == 200
    for j in filtered_res.json():
        assert j["status"] == "pending"
