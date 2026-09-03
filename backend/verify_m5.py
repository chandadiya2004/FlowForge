"""Milestone 5 End-to-End Verification Script.

Tests a 3-step workflow where:
  - Step 1: log_message (succeeds)
  - Step 2: http_call to a non-existent port (fails)
  - Step 3: log_message (should never start)
Verifies state transitions: pending -> running -> failed.
"""

import time
import httpx

SERVER_URL = "http://127.0.0.1:8000"


def main():
    print("=== FlowForge Milestone 5 E2E Verification ===")

    # 1. Register & Login
    email = "m5_user@flowforge.dev"
    pw = "Password123!"
    httpx.post(f"{SERVER_URL}/auth/register", json={"email": email, "password": pw})
    login_res = httpx.post(f"{SERVER_URL}/auth/login", json={"email": email, "password": pw})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] User authenticated and token obtained.")

    # 2. Create 3-step workflow (Middle step fails)
    wf_payload = {
        "name": "Failure-Path 3-Step Pipeline",
        "description": "Demonstrates sequential failure stop",
        "definition": [
            {
                "name": "Step 1 - Log Start",
                "type": "log_message",
                "config": {"message": "Pipeline initiated"},
            },
            {
                "name": "Step 2 - Broken HTTP Call",
                "type": "http_call",
                "config": {"url": "http://127.0.0.1:9999/nonexistent", "method": "GET", "timeout": 2.0},
            },
            {
                "name": "Step 3 - Should Never Execute",
                "type": "log_message",
                "config": {"message": "This should never run"},
            },
        ],
    }
    wf_res = httpx.post(f"{SERVER_URL}/workflows", json=wf_payload, headers=headers)
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]
    print(f"[PASS] Created 3-step workflow (id: {wf_id})")

    # 3. Create Job
    job_res = httpx.post(f"{SERVER_URL}/workflows/{wf_id}/jobs", headers=headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]
    print(f"[PASS] Created Job (id: {job_id}, status: {job_res.json()['status']})")
    assert job_res.json()["status"] == "pending"

    # 4. Trigger Job
    trigger_res = httpx.post(f"{SERVER_URL}/jobs/{job_id}/trigger", headers=headers)
    assert trigger_res.status_code == 200
    print(f"[PASS] Triggered Job via POST /jobs/{job_id}/trigger")

    # 5. Poll Job Details to observe lifecycle
    print("\nPolling GET /jobs/{job_id}...")
    for attempt in range(1, 15):
        poll_res = httpx.get(f"{SERVER_URL}/jobs/{job_id}", headers=headers)
        assert poll_res.status_code == 200
        job_data = poll_res.json()
        current_status = job_data["status"]
        tasks = job_data.get("tasks", [])
        task_states = [f"{t['name']}: {t['status']}" for t in tasks]
        print(f"  Poll {attempt:02d}: Job Status='{current_status}' | Tasks: [{', '.join(task_states)}]")

        if current_status == "failed":
            print("\n[SUCCESS] Job reached expected 'failed' terminal status!")
            assert tasks[0]["status"] == "completed", f"Task 1 should be completed, got {tasks[0]['status']}"
            assert tasks[1]["status"] == "failed", f"Task 2 should be failed, got {tasks[1]['status']}"
            assert tasks[1]["error_message"] is not None, "Task 2 should record error message"
            assert tasks[2]["status"] == "pending", f"Task 3 must remain pending, got {tasks[2]['status']}"
            assert tasks[2]["started_at"] is None, "Task 3 must not have started"
            print(f"  -> Task 1 output: {tasks[0]['output_data']}")
            print(f"  -> Task 2 error: {tasks[1]['error_message'][:80]}...")
            print(f"  -> Task 3 status: {tasks[2]['status']} (never started, as expected)")
            break

        time.sleep(0.8)
    else:
        raise TimeoutError(f"Job {job_id} did not reach 'failed' status within timeout.")

    print("\n>>> ALL MILESTONE 5 VERIFICATION CHECKS PASSED! <<<")


if __name__ == "__main__":
    main()
