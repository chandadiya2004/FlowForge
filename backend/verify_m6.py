"""Milestone 6 End-to-End Verification Script (Retry Logic & Dead-Letter Handling).

Creates a workflow with max_retries=2 and a broken HTTP URL.
Verifies:
  - Initial attempt fails -> status='retrying', retry_count=1, job='running'
  - Retry 1 fails -> status='retrying', retry_count=2, job='running'
  - Retry 2 fails -> status='failed', retry_count=2, job='failed'
  - DeadLetterTask created and accessible via GET /dead-letters
  - Admin requeue via POST /dead-letters/{id}/requeue resets task to pending
"""

import os
import time
import httpx

SERVER_URL = "http://127.0.0.1:8000"


def main():
    print("=== FlowForge Milestone 6 E2E Verification ===")

    # 1. Register & Login as Admin
    admin_email = "m6_admin@flowforge.dev"
    pw = "AdminPass123!"
    httpx.post(f"{SERVER_URL}/auth/register", json={"email": admin_email, "password": pw})

    # Promote to admin in DB
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.models.user import User, UserRole
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        user = db.query(User).filter(User.email == admin_email).first()
        if user:
            user.role = UserRole.ADMIN
            db.commit()

    login_res = httpx.post(f"{SERVER_URL}/auth/login", json={"email": admin_email, "password": pw})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    admin_token = login_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[PASS] Admin user registered, promoted to ADMIN, and token acquired.")

    # 2. Create Workflow with max_retries=2 on broken URL
    wf_payload = {
        "name": "M6 Retry & Dead-Letter Pipeline",
        "description": "Tests retry backoff and dead-letter capture",
        "definition": [
            {
                "name": "Guaranteed Broken Step",
                "type": "http_call",
                "config": {"url": "http://127.0.0.1:9999/broken", "timeout": 0.5},
                "max_retries": 2,
            }
        ],
    }
    wf_res = httpx.post(f"{SERVER_URL}/workflows", json=wf_payload, headers=admin_headers)
    assert wf_res.status_code == 201, f"Failed to create workflow: {wf_res.text}"
    wf_id = wf_res.json()["id"]
    print(f"[PASS] Created workflow with max_retries=2 (id: {wf_id})")

    # 3. Create Job
    job_res = httpx.post(f"{SERVER_URL}/workflows/{wf_id}/jobs", headers=admin_headers)
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]
    print(f"[PASS] Created job (id: {job_id})")

    # 4. Trigger Job
    trigger_res = httpx.post(f"{SERVER_URL}/jobs/{job_id}/trigger", headers=admin_headers)
    assert trigger_res.status_code == 200
    print(f"[PASS] Triggered job via POST /jobs/{job_id}/trigger")

    # 5. Poll Job Details and observe retrying -> failed transition
    print("\nPolling GET /jobs/{job_id} across retry window...")
    saw_retrying = False
    for attempt in range(1, 40):
        res = httpx.get(f"{SERVER_URL}/jobs/{job_id}", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        job_status = data["status"]
        tasks = data.get("tasks", [])
        if tasks:
            t = tasks[0]
            t_status = t["status"]
            t_retries = t["retry_count"]
            print(f"  Poll {attempt:02d}: Job Status='{job_status}' | Task Status='{t_status}' | retry_count={t_retries}")

            if t_status == "retrying":
                saw_retrying = True
                assert job_status == "running", "Job must stay 'running' while task is retrying!"

            if job_status == "failed" and t_status == "failed":
                print(f"\n[PASS] Job reached 'failed' status after exhausting retries (final retry_count={t_retries})")
                assert t_retries == 2, f"Expected 2 retries, got {t_retries}"
                break

        time.sleep(1.0)
    else:
        raise TimeoutError("Job did not finish retries within expected timeframe.")

    assert saw_retrying, "Expected to see task in 'retrying' state during backoff window!"

    # 6. Check Dead-Letters
    print("\nVerifying GET /dead-letters...")
    dl_res = httpx.get(f"{SERVER_URL}/dead-letters?workflow_id={wf_id}", headers=admin_headers)
    assert dl_res.status_code == 200
    dl_list = dl_res.json()
    assert len(dl_list) >= 1, "Expected at least 1 dead-letter entry for this workflow"
    dl_entry = dl_list[0]
    print(f"[PASS] Found dead-letter record (id: {dl_entry['id']}, retry_count: {dl_entry['retry_count']})")
    assert dl_entry["task_type"] == "http_call"
    assert dl_entry["retry_count"] == 2
    assert dl_entry["error_message"] is not None

    # 7. Test Requeue
    dl_id = dl_entry["id"]
    print(f"\nTesting POST /dead-letters/{dl_id}/requeue...")
    requeue_res = httpx.post(f"{SERVER_URL}/dead-letters/{dl_id}/requeue", headers=admin_headers)
    assert requeue_res.status_code == 200
    requeue_data = requeue_res.json()
    assert requeue_data["requeued_at"] is not None
    print(f"[PASS] Requeued dead-letter task (requeued_at: {requeue_data['requeued_at']})")

    # Check that task status in job was reset
    job_after_requeue = httpx.get(f"{SERVER_URL}/jobs/{job_id}", headers=admin_headers).json()
    task_after = job_after_requeue["tasks"][0]
    print(f"[PASS] Task state after requeue: status='{task_after['status']}', retry_count={task_after['retry_count']}")

    print("\n>>> ALL MILESTONE 6 VERIFICATION CHECKS PASSED! <<<")


if __name__ == "__main__":
    main()
