import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Add worker directory to sys.path
worker_path = Path(__file__).resolve().parent.parent.parent / "worker"
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

from app.core.queue_routing import (
    DEFAULT_QUEUE,
    HIGH_QUEUE,
    LOW_QUEUE,
    get_queue_for_priority,
)
from app.core.security import create_access_token, get_password_hash
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.models.workflow import Workflow
from main import app
from tasks.orchestrate import handle_task_completion
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def create_user(email: str, role: UserRole = UserRole.MEMBER):
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=get_password_hash("testpass"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    token = create_access_token(data={"sub": str(user_id), "role": role.value})
    return user_id, token


def test_get_queue_for_priority_mapping():
    # High: 1-3
    assert get_queue_for_priority(1) == HIGH_QUEUE
    assert get_queue_for_priority(2) == HIGH_QUEUE
    assert get_queue_for_priority(3) == HIGH_QUEUE

    # Default: 4-7
    assert get_queue_for_priority(4) == DEFAULT_QUEUE
    assert get_queue_for_priority(5) == DEFAULT_QUEUE
    assert get_queue_for_priority(6) == DEFAULT_QUEUE
    assert get_queue_for_priority(7) == DEFAULT_QUEUE

    # Low: 8-10
    assert get_queue_for_priority(8) == LOW_QUEUE
    assert get_queue_for_priority(9) == LOW_QUEUE
    assert get_queue_for_priority(10) == LOW_QUEUE

    # Fallbacks
    assert get_queue_for_priority(0) == DEFAULT_QUEUE
    assert get_queue_for_priority(15) == DEFAULT_QUEUE


def test_create_job_with_priority():
    user_id, token = create_user("pq_create@example.com")
    db = TestingSessionLocal()
    wf = Workflow(
        id=uuid.uuid4(),
        name="Priority WF",
        owner_id=user_id,
        definition=[{"name": "Step 1", "type": "sleep", "config": {"seconds": 1}}],
        is_active=True,
    )
    db.add(wf)
    db.commit()
    wf_id = wf.id
    db.close()

    # 1. Default priority when not specified -> 5
    res_def = client.post(f"/workflows/{wf_id}/jobs", headers={"Authorization": f"Bearer {token}"})
    assert res_def.status_code == 201
    assert res_def.json()["priority"] == 5

    # 2. Custom high priority -> 2
    res_high = client.post(
        f"/workflows/{wf_id}/jobs",
        json={"priority": 2},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_high.status_code == 201
    assert res_high.json()["priority"] == 2

    # 3. Custom low priority -> 9
    res_low = client.post(
        f"/workflows/{wf_id}/jobs",
        json={"priority": 9},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_low.status_code == 201
    assert res_low.json()["priority"] == 9

    # 4. Out of range priority -> 422
    res_invalid = client.post(
        f"/workflows/{wf_id}/jobs",
        json={"priority": 12},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_invalid.status_code == 422


def test_update_job_priority():
    user_id, token = create_user("pq_update@example.com")
    other_user_id, other_token = create_user("pq_other@example.com")
    db = TestingSessionLocal()
    wf = Workflow(id=uuid.uuid4(), name="WF Priority Update", owner_id=user_id, definition=[], is_active=True)
    pending_job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user_id, status=JobStatus.PENDING, priority=5)
    running_job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user_id, status=JobStatus.RUNNING, priority=5)
    db.add_all([wf, pending_job, running_job])
    db.commit()
    pending_id = pending_job.id
    running_id = running_job.id
    db.close()

    # Successful priority update on pending job
    res = client.put(
        f"/jobs/{pending_id}/priority",
        json={"priority": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["priority"] == 1

    # 409 Conflict when updating running job
    res_running = client.put(
        f"/jobs/{running_id}/priority",
        json={"priority": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_running.status_code == 409

    # 403 Forbidden when non-owner updates priority
    res_forbidden = client.put(
        f"/jobs/{pending_id}/priority",
        json={"priority": 2},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert res_forbidden.status_code == 403


def test_trigger_dispatches_to_correct_queues():
    user_id, token = create_user("pq_dispatch@example.com")
    db = TestingSessionLocal()
    wf = Workflow(id=uuid.uuid4(), name="Dispatch WF", owner_id=user_id, definition=[], is_active=True)

    job_high = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user_id, status=JobStatus.PENDING, priority=2)
    t_high = Task(id=uuid.uuid4(), job_id=job_high.id, name="TH", type="sleep", sequence=1, status=TaskStatus.PENDING)

    job_default = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user_id, status=JobStatus.PENDING, priority=6)
    t_default = Task(id=uuid.uuid4(), job_id=job_default.id, name="TD", type="sleep", sequence=1, status=TaskStatus.PENDING)

    job_low = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user_id, status=JobStatus.PENDING, priority=10)
    t_low = Task(id=uuid.uuid4(), job_id=job_low.id, name="TL", type="sleep", sequence=1, status=TaskStatus.PENDING)

    db.add_all([wf, job_high, t_high, job_default, t_default, job_low, t_low])
    db.commit()
    jh_id = job_high.id
    th_id = str(t_high.id)
    jd_id = job_default.id
    td_id = str(t_default.id)
    jl_id = job_low.id
    tl_id = str(t_low.id)
    db.close()

    with patch("app.api.jobs.dispatch_task") as mock_dispatch:
        # High priority -> "high" queue
        client.post(f"/jobs/{jh_id}/trigger", headers={"Authorization": f"Bearer {token}"})
        mock_dispatch.assert_called_with("execute_task", args=[th_id], queue=HIGH_QUEUE)

        # Default priority -> "default" queue
        client.post(f"/jobs/{jd_id}/trigger", headers={"Authorization": f"Bearer {token}"})
        mock_dispatch.assert_called_with("execute_task", args=[td_id], queue=DEFAULT_QUEUE)

        # Low priority -> "low" queue
        client.post(f"/jobs/{jl_id}/trigger", headers={"Authorization": f"Bearer {token}"})
        mock_dispatch.assert_called_with("execute_task", args=[tl_id], queue=LOW_QUEUE)


def test_orchestration_preserves_priority_queue():
    db = TestingSessionLocal()
    user_id, _ = create_user("pq_orch@example.com")
    wf = Workflow(id=uuid.uuid4(), name="Orch WF", owner_id=user_id, definition=[], is_active=True)
    job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user_id, status=JobStatus.RUNNING, priority=1)
    task1 = Task(id=uuid.uuid4(), job_id=job.id, name="T1", type="log_message", sequence=1, status=TaskStatus.COMPLETED)
    task2 = Task(id=uuid.uuid4(), job_id=job.id, name="T2", type="log_message", sequence=2, status=TaskStatus.PENDING)
    db.add_all([wf, job, task1, task2])
    db.commit()
    t1_id = task1.id
    t2_id = str(task2.id)

    with patch("tasks.execute_task.execute_task.apply_async") as mock_apply:
        handle_task_completion(t1_id, db)
        mock_apply.assert_called_once_with(args=[t2_id], queue=HIGH_QUEUE)

    db.close()
