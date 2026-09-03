"""Milestone 3 End-to-End Verification Script (Workflows & Jobs)."""

import httpx

SERVER_URL = "http://127.0.0.1:8000"


def main():
    print("=== FlowForge Milestone 3 E2E Verification ===")

    # 1. Register / Login User
    user_email = "m3_user@flowforge.dev"
    user_pw = "Password123!"
    httpx.post(f"{SERVER_URL}/auth/register", json={"email": user_email, "password": user_pw})

    login_res = httpx.post(f"{SERVER_URL}/auth/login", json={"email": user_email, "password": user_pw})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] Authenticated user and acquired JWT access token")

    # 2. Create Workflow with a 2-step definition
    wf_payload = {
        "name": "Data Ingestion Pipeline",
        "description": "Extract raw data and transform into clean format",
        "definition": [
            {
                "name": "Extract Records",
                "type": "http_extractor",
                "config": {"source_url": "https://api.example.com/data", "format": "json"},
            },
            {
                "name": "Transform Schema",
                "type": "schema_validator",
                "config": {"strict_mode": True, "drop_nulls": True},
            },
        ],
    }
    wf_res = httpx.post(f"{SERVER_URL}/workflows", json=wf_payload, headers=headers)
    assert wf_res.status_code == 201, f"Workflow creation failed: {wf_res.text}"
    workflow = wf_res.json()
    wf_id = workflow["id"]
    assert len(workflow["definition"]) == 2
    print(f"[PASS] POST /workflows -> 201 Created (workflow_id: {wf_id}, 2-step definition)")

    # 3. Create a Job from the Workflow
    job_res = httpx.post(f"{SERVER_URL}/workflows/{wf_id}/jobs", headers=headers)
    assert job_res.status_code == 201, f"Job creation failed: {job_res.text}"
    created_job = job_res.json()
    job_id = created_job["id"]
    assert created_job["status"] == "pending"
    assert created_job["workflow_id"] == wf_id
    assert len(created_job["tasks"]) == 2
    print(f"[PASS] POST /workflows/{wf_id}/jobs -> 201 Created (job_id: {job_id}, status: pending)")

    # 4. Fetch the Job by ID and confirm nested tasks in sequence order
    get_job_res = httpx.get(f"{SERVER_URL}/jobs/{job_id}", headers=headers)
    assert get_job_res.status_code == 200, f"Fetch job failed: {get_job_res.text}"
    job_detail = get_job_res.json()
    tasks = job_detail["tasks"]
    assert len(tasks) == 2, f"Expected 2 tasks, got {len(tasks)}"

    task1, task2 = tasks[0], tasks[1]
    assert task1["sequence"] == 1 and task1["name"] == "Extract Records" and task1["status"] == "pending"
    assert task2["sequence"] == 2 and task2["name"] == "Transform Schema" and task2["status"] == "pending"
    print("[PASS] GET /jobs/{id} -> 200 OK:")
    print(f"       - Task 1: name='{task1['name']}', sequence={task1['sequence']}, status='{task1['status']}'")
    print(f"       - Task 2: name='{task2['name']}', sequence={task2['sequence']}, status='{task2['status']}'")

    # 5. Fetch specific tasks endpoint
    tasks_res = httpx.get(f"{SERVER_URL}/jobs/{job_id}/tasks", headers=headers)
    assert tasks_res.status_code == 200
    assert len(tasks_res.json()) == 2
    print(f"[PASS] GET /jobs/{job_id}/tasks -> 200 OK (returned 2 ordered task items)")

    # 6. List jobs with status filter
    list_res = httpx.get(f"{SERVER_URL}/jobs?status=pending", headers=headers)
    assert list_res.status_code == 200
    assert any(j["id"] == job_id for j in list_res.json())
    print("[PASS] GET /jobs?status=pending -> 200 OK (matched pending job)")

    print("\n>>> ALL MILESTONE 3 VERIFICATION CHECKS PASSED! <<<")


if __name__ == "__main__":
    main()
