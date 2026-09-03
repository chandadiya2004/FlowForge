import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

# Add worker directory to sys.path so tests can import worker modules
worker_path = Path(__file__).resolve().parent.parent.parent / "worker"
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

from app.core.security import create_access_token, get_password_hash
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.models.workflow import Workflow
from main import app
from tasks.registry import get_handler, handle_log_message, handle_sleep, handle_http_call
from tasks.orchestrate import handle_task_completion
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def create_test_user_and_token(email: str, role: UserRole = UserRole.MEMBER):
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
    db.refresh(user)
    db.close()
    token = create_access_token(data={"sub": str(user.id), "role": role.value})
    return user, token


def test_task_registry_handlers():
    # 1. log_message
    res = handle_log_message({"message": "Hello FlowForge"})
    assert res == {"logged": "Hello FlowForge"}

    # 2. sleep
    res = handle_sleep({"seconds": 0.01})
    assert res == {"slept": 0.01}

    # 3. unknown type raises ValueError
    with pytest.raises(ValueError, match="Unsupported task type"):
        get_handler("non_existent_type")


def test_http_call_handler():
    # Mocking httpx for http_call test
    with patch("httpx.Client.request") as mock_req:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "mocked response body"
        mock_req.return_value = mock_resp

        res = handle_http_call({"url": "https://example.com/api", "method": "GET"})
        assert res["status_code"] == 200
        assert "mocked response" in res["body"]


def test_trigger_job_endpoint_success():
    user, token = create_test_user_and_token("runner_trigger@example.com")
    db = TestingSessionLocal()

    wf = Workflow(
        id=uuid.uuid4(),
        name="Trigger Test Flow",
        owner_id=user.id,
        definition=[{"name": "Step 1", "type": "log_message", "config": {"message": "hi"}}],
        is_active=True,
    )
    job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user.id, status=JobStatus.PENDING)
    task1 = Task(id=uuid.uuid4(), job_id=job.id, name="Step 1", type="log_message", sequence=1, status=TaskStatus.PENDING)
    db.add_all([wf, job, task1])
    db.commit()
    job_id = job.id
    task1_id = task1.id
    db.close()

    with patch("app.api.jobs.dispatch_task") as mock_dispatch:
        res = client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == str(job_id)
        mock_dispatch.assert_called_once_with("execute_task", args=[str(task1_id)])


def test_trigger_job_non_pending_returns_409():
    user, token = create_test_user_and_token("already_running@example.com")
    db = TestingSessionLocal()

    wf = Workflow(
        id=uuid.uuid4(),
        name="Running Flow",
        owner_id=user.id,
        definition=[{"name": "Step 1", "type": "sleep", "config": {}}],
        is_active=True,
    )
    job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user.id, status=JobStatus.RUNNING)
    db.add_all([wf, job])
    db.commit()
    job_id = job.id
    db.close()

    res = client.post(f"/jobs/{job_id}/trigger", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 409
    assert "Only 'pending' jobs can be triggered" in res.json()["detail"]


def test_orchestration_failure_halts_job():
    db = TestingSessionLocal()
    user = User(id=uuid.uuid4(), email="orch_fail@example.com", hashed_password="pw", role=UserRole.MEMBER, is_active=True)
    wf = Workflow(id=uuid.uuid4(), name="Fail Flow", owner_id=user.id, definition=[], is_active=True)
    job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user.id, status=JobStatus.RUNNING)
    task1 = Task(id=uuid.uuid4(), job_id=job.id, name="Task 1", type="http_call", sequence=1, status=TaskStatus.FAILED)
    task2 = Task(id=uuid.uuid4(), job_id=job.id, name="Task 2", type="log_message", sequence=2, status=TaskStatus.PENDING)
    db.add_all([user, wf, job, task1, task2])
    db.commit()

    handle_task_completion(task1.id, db)

    # Job should now be FAILED, task 2 remains PENDING
    db.refresh(job)
    db.refresh(task2)
    assert job.status == JobStatus.FAILED
    assert job.completed_at is not None
    assert task2.status == TaskStatus.PENDING
    db.close()


def test_orchestration_progression_and_completion():
    db = TestingSessionLocal()
    user = User(id=uuid.uuid4(), email="orch_prog@example.com", hashed_password="pw", role=UserRole.MEMBER, is_active=True)
    wf = Workflow(id=uuid.uuid4(), name="Prog Flow", owner_id=user.id, definition=[], is_active=True)
    job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user.id, status=JobStatus.RUNNING)
    task1 = Task(id=uuid.uuid4(), job_id=job.id, name="Task 1", type="log_message", sequence=1, status=TaskStatus.COMPLETED)
    task2 = Task(id=uuid.uuid4(), job_id=job.id, name="Task 2", type="log_message", sequence=2, status=TaskStatus.PENDING)
    db.add_all([user, wf, job, task1, task2])
    db.commit()

    with patch("tasks.execute_task.execute_task.delay") as mock_delay:
        handle_task_completion(task1.id, db)
        # Should dispatch next task in sequence
        mock_delay.assert_called_once_with(str(task2.id))

    # Now simulate task2 completing
    task2.status = TaskStatus.COMPLETED
    db.commit()
    handle_task_completion(task2.id, db)

    # All tasks finished -> job should be COMPLETED
    db.refresh(job)
    assert job.status == JobStatus.COMPLETED
    assert job.completed_at is not None
    db.close()
