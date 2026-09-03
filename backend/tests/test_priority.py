from unittest.mock import patch
from fastapi.testclient import TestClient
import pytest

from app.core.queue_routing import get_queue_for_priority
from app.models.job import JobStatus


@pytest.mark.parametrize(
    "priority, expected_queue",
    [
        (1, "high"),
        (2, "high"),
        (3, "high"),      # Tier 1-3 boundary
        (4, "default"),   # Tier 4-7 boundary
        (5, "default"),
        (6, "default"),
        (7, "default"),   # Tier 4-7 boundary
        (8, "low"),       # Tier 8-10 boundary
        (9, "low"),
        (10, "low"),
        (0, "default"),   # Out-of-range fallback
        (-5, "default"),  # Out-of-range fallback
        (15, "default"),  # Out-of-range fallback
    ],
)
def test_get_queue_for_priority_all_tiers_and_boundaries(priority: int, expected_queue: str):
    """Verifies queue selection across all tiered ranges and edge boundaries."""
    assert get_queue_for_priority(priority) == expected_queue


def test_job_dispatch_routes_to_high_priority_queue(client: TestClient, member_token: str):
    """Verifies that triggering a priority 2 job dispatches to the 'high' queue."""
    wf_res = client.post(
        "/workflows",
        json={"name": "High Priority WF", "definition": [{"name": "Step", "type": "log_message", "config": {}}]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    job_res = client.post(
        f"/workflows/{wf_id}/jobs",
        json={"priority": 2},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    with patch("app.api.jobs.dispatch_task") as mock_dispatch:
        trigger_res = client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {member_token}"})
        assert trigger_res.status_code == 200
        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        assert kwargs.get("queue") == "high"


def test_job_dispatch_routes_to_low_priority_queue(client: TestClient, member_token: str):
    """Verifies that triggering a priority 9 job dispatches to the 'low' queue."""
    wf_res = client.post(
        "/workflows",
        json={"name": "Low Priority WF", "definition": [{"name": "Step", "type": "log_message", "config": {}}]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    job_res = client.post(
        f"/workflows/{wf_id}/jobs",
        json={"priority": 9},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    with patch("app.api.jobs.dispatch_task") as mock_dispatch:
        trigger_res = client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {member_token}"})
        assert trigger_res.status_code == 200
        mock_dispatch.assert_called_once()
        _, kwargs = mock_dispatch.call_args
        assert kwargs.get("queue") == "low"


def test_update_job_priority_when_pending(client: TestClient, member_token: str):
    """Verifies updating job priority while pending succeeds."""
    wf_res = client.post(
        "/workflows",
        json={"name": "Priority Update WF", "definition": [{"name": "Step", "type": "log_message", "config": {}}]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    job_res = client.post(f"/workflows/{wf_id}/jobs", json={"priority": 5}, headers={"Authorization": f"Bearer {member_token}"})
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    update_res = client.put(
        f"/jobs/{job_id}/priority",
        json={"priority": 1},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["priority"] == 1


def test_update_job_priority_rejected_when_not_pending(client: TestClient, member_token: str):
    """Verifies updating job priority on a running or completed job returns 409 Conflict."""
    wf_res = client.post(
        "/workflows",
        json={"name": "Conflict WF", "definition": [{"name": "Step", "type": "log_message", "config": {}}]},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    job_res = client.post(f"/workflows/{wf_id}/jobs", json={"priority": 5}, headers={"Authorization": f"Bearer {member_token}"})
    assert job_res.status_code == 201
    job_id = job_res.json()["id"]

    # Trigger job in eager mode -> completes
    client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {member_token}"})

    # Try to change priority on completed job
    conflict_res = client.put(
        f"/jobs/{job_id}/priority",
        json={"priority": 2},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert conflict_res.status_code == 409
    assert "Only 'pending' jobs" in conflict_res.json()["detail"]
