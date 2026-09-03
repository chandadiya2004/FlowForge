"""Milestone 4 End-to-End Verification Script (Redis & Celery Pipeline)."""

import time
import httpx

SERVER_URL = "http://127.0.0.1:8000"


def main():
    print("=== FlowForge Milestone 4 E2E Verification ===")

    # 1. Dispatch ping task via HTTP POST
    print("Dispatching ping task via POST /system/ping-worker ...")
    res = httpx.post(f"{SERVER_URL}/system/ping-worker")
    assert res.status_code == 202, f"Failed to dispatch ping: {res.text}"
    data = res.json()
    task_id = data["task_id"]
    print(f"[PASS] POST /system/ping-worker -> 202 Accepted (task_id: {task_id})")

    # 2. Poll /system/task-result/{task_id}
    print(f"Polling GET /system/task-result/{task_id} ...")
    max_retries = 15
    for attempt in range(1, max_retries + 1):
        status_res = httpx.get(f"{SERVER_URL}/system/task-result/{task_id}")
        assert status_res.status_code == 200, f"Failed to query task result: {status_res.text}"
        status_data = status_res.json()
        current_status = status_data["status"]
        current_result = status_data["result"]
        print(f"  Attempt {attempt}: status={current_status}, result={current_result}")

        if current_status == "SUCCESS":
            assert current_result == "pong", f"Expected result 'pong', got {current_result}"
            print("[PASS] Task reached SUCCESS with result: 'pong'!")
            break
        elif current_status == "FAILURE":
            raise RuntimeError(f"Task failed unexpectedly: {current_result}")

        time.sleep(0.5)
    else:
        raise TimeoutError(f"Task {task_id} did not finish within {max_retries * 0.5} seconds.")

    print("\n>>> ALL MILESTONE 4 VERIFICATION CHECKS PASSED! <<<")


if __name__ == "__main__":
    main()
