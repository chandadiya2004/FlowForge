"""Milestone 7 End-to-End Verification Script (Priority Queue Preemption).

Demonstrates that high-priority tasks in the "high" queue are consumed
ahead of queued tasks in the "low" queue by a worker listening on:
  -Q high,default,low
"""

import time
import httpx

SERVER_URL = "http://127.0.0.1:8000"


def main():
    print("=== FlowForge Milestone 7 E2E Verification ===")

    # 1. Login
    email = "m7_user@flowforge.dev"
    pw = "Password123!"
    httpx.post(f"{SERVER_URL}/auth/register", json={"email": email, "password": pw})
    login_res = httpx.post(f"{SERVER_URL}/auth/login", json={"email": email, "password": pw})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] User authenticated.")

    # 2. Create Workflow
    wf_payload = {
        "name": "Priority Preemption Workflow",
        "description": "Demonstrates queue ordering with sleep tasks",
        "definition": [
            {
                "name": "Work Step",
                "type": "sleep",
                "config": {"seconds": 2.0},
            }
        ],
    }
    wf_res = httpx.post(f"{SERVER_URL}/workflows", json=wf_payload, headers=headers)
    assert wf_res.status_code == 201, f"Failed to create workflow: {wf_res.text}"
    wf_id = wf_res.json()["id"]
    print(f"[PASS] Created workflow (id: {wf_id})")

    # 3. Create 3 Low-Priority Jobs (priority=10 -> 'low' queue)
    low_job_ids = []
    for i in range(1, 4):
        res = httpx.post(
            f"{SERVER_URL}/workflows/{wf_id}/jobs",
            json={"priority": 10},
            headers=headers,
        )
        assert res.status_code == 201
        job_id = res.json()["id"]
        low_job_ids.append(job_id)
        print(f"[PASS] Created Low-Priority Job #{i} (id: {job_id}, priority: 10 -> 'low' queue)")

    # 4. Trigger all 3 Low-Priority Jobs
    print("\nTriggering 3 Low-Priority Jobs into 'low' queue...")
    for jid in low_job_ids:
        trig = httpx.post(f"{SERVER_URL}/jobs/{jid}/trigger", headers=headers)
        assert trig.status_code == 200

    # Brief pause to allow worker to pick up the first job
    time.sleep(0.5)

    # 5. Create and Trigger 1 High-Priority Job (priority=1 -> 'high' queue)
    print("\nCreating & Triggering High-Priority Job (priority: 1 -> 'high' queue)...")
    high_res = httpx.post(
        f"{SERVER_URL}/workflows/{wf_id}/jobs",
        json={"priority": 1},
        headers=headers,
    )
    assert high_res.status_code == 201
    high_job_id = high_res.json()["id"]

    trig_high = httpx.post(f"{SERVER_URL}/jobs/{high_job_id}/trigger", headers=headers)
    assert trig_high.status_code == 200
    print(f"[PASS] High-Priority Job dispatched (id: {high_job_id})")

    # 6. Monitor completion order
    print("\nMonitoring execution order via GET /jobs...")
    high_completed_first = False
    start_time = time.time()
    while time.time() - start_time < 20:
        # Check high job status
        hj = httpx.get(f"{SERVER_URL}/jobs/{high_job_id}", headers=headers).json()
        # Check low jobs status
        low_statuses = [httpx.get(f"{SERVER_URL}/jobs/{jid}", headers=headers).json()["status"] for jid in low_job_ids]

        print(f"  Status Check: High Job='{hj['status']}' | Low Jobs={low_statuses}")

        if hj["status"] == "completed":
            # Verify at least one low-priority job is NOT completed yet
            incomplete_low_jobs = [s for s in low_statuses if s != "completed"]
            print(f"\n>>> High-priority job completed while low-priority backlog remaining: {incomplete_low_jobs} <<<")
            assert len(incomplete_low_jobs) >= 1, "Expected low-priority jobs to still be queued/running!"
            high_completed_first = True
            break

        time.sleep(0.6)

    assert high_completed_first, "High-priority job failed to preempt low-priority queue!"
    print("\n>>> ALL MILESTONE 7 VERIFICATION CHECKS PASSED! <<<")


if __name__ == "__main__":
    main()
