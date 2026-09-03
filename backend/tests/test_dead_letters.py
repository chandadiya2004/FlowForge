import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

# Add worker directory to sys.path
worker_path = Path(__file__).resolve().parent.parent.parent / "worker"
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

from app.core.security import create_access_token, get_password_hash
from app.models.dead_letter import DeadLetterTask
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.models.workflow import Workflow
from main import app
from tasks.execute_task import execute_task
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


def test_dead_letters_admin_only():
    admin_id, admin_token = create_user("dl_admin@example.com", UserRole.ADMIN)
    member_id, member_token = create_user("dl_member@example.com", UserRole.MEMBER)

    # Member gets 403 Forbidden
    res = client.get("/dead-letters", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 403

    # Admin gets 200 OK
    res = client.get("/dead-letters", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_dead_letter_list_and_filter():
    admin_id, admin_token = create_user("dl_filter_admin@example.com", UserRole.ADMIN)
    db = TestingSessionLocal()

    wf1 = Workflow(id=uuid.uuid4(), name="WF 1", owner_id=admin_id, definition=[], is_active=True)
    wf2 = Workflow(id=uuid.uuid4(), name="WF 2", owner_id=admin_id, definition=[], is_active=True)
    job1 = Job(id=uuid.uuid4(), workflow_id=wf1.id, triggered_by=admin_id, status=JobStatus.FAILED)
    job2 = Job(id=uuid.uuid4(), workflow_id=wf2.id, triggered_by=admin_id, status=JobStatus.FAILED)
    t1 = Task(id=uuid.uuid4(), job_id=job1.id, name="T1", type="http_call", sequence=1, status=TaskStatus.FAILED)
    t2 = Task(id=uuid.uuid4(), job_id=job2.id, name="T2", type="http_call", sequence=1, status=TaskStatus.FAILED)

    dl1 = DeadLetterTask(
        id=uuid.uuid4(),
        task_id=t1.id,
        job_id=job1.id,
        workflow_id=wf1.id,
        task_type="http_call",
        error_message="Connection refused",
        retry_count=3,
        failed_at=datetime.now(timezone.utc),
    )
    dl2 = DeadLetterTask(
        id=uuid.uuid4(),
        task_id=t2.id,
        job_id=job2.id,
        workflow_id=wf2.id,
        task_type="http_call",
        error_message="Gateway timeout",
        retry_count=3,
        failed_at=datetime.now(timezone.utc),
    )
    db.add_all([wf1, wf2, job1, job2, t1, t2, dl1, dl2])
    db.commit()
    dl1_id = dl1.id
    wf1_id = wf1.id
    db.close()

    # Filter by wf1
    res = client.get(f"/dead-letters?workflow_id={wf1_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert all(item["workflow_id"] == str(wf1_id) for item in data)

    # Detail view
    res_detail = client.get(f"/dead-letters/{dl1_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == str(dl1_id)
    assert res_detail.json()["error_message"] == "Connection refused"


def test_dead_letter_requeue():
    admin_id, admin_token = create_user("dl_requeue_admin@example.com", UserRole.ADMIN)
    db = TestingSessionLocal()

    wf = Workflow(id=uuid.uuid4(), name="Requeue WF", owner_id=admin_id, definition=[], is_active=True)
    job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=admin_id, status=JobStatus.FAILED)
    t = Task(
        id=uuid.uuid4(),
        job_id=job.id,
        name="Failed Task",
        type="http_call",
        sequence=1,
        status=TaskStatus.FAILED,
        retry_count=3,
        error_message="Old error",
    )
    dl = DeadLetterTask(
        id=uuid.uuid4(),
        task_id=t.id,
        job_id=job.id,
        workflow_id=wf.id,
        task_type="http_call",
        error_message="Old error",
        retry_count=3,
        failed_at=datetime.now(timezone.utc),
    )
    db.add_all([wf, job, t, dl])
    db.commit()
    dl_id = dl.id
    t_id = t.id
    job_id = job.id
    db.close()

    with patch("app.api.dead_letters.dispatch_task") as mock_dispatch:
        res = client.post(f"/dead-letters/{dl_id}/requeue", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.json()
        assert data["requeued_at"] is not None
        mock_dispatch.assert_called_once_with("execute_task", args=[str(t_id)], queue="default")

    # Verify task and job status reset in database
    db2 = TestingSessionLocal()
    refreshed_task = db2.query(Task).filter(Task.id == t_id).first()
    refreshed_job = db2.query(Job).filter(Job.id == job_id).first()
    assert refreshed_task.status == TaskStatus.PENDING
    assert refreshed_task.retry_count == 0
    assert refreshed_task.error_message is None
    assert refreshed_job.status == JobStatus.RUNNING
    db2.close()


def test_execute_task_retries_then_dead_letters():
    db = TestingSessionLocal()
    user_id, _ = create_user("runner_retry@example.com", UserRole.MEMBER)

    wf = Workflow(id=uuid.uuid4(), name="Retry Flow", owner_id=user_id, definition=[], is_active=True)
    job = Job(id=uuid.uuid4(), workflow_id=wf.id, triggered_by=user_id, status=JobStatus.RUNNING)
    task = Task(
        id=uuid.uuid4(),
        job_id=job.id,
        name="Broken Task",
        type="http_call",
        sequence=1,
        status=TaskStatus.PENDING,
        input_data={"url": "http://127.0.0.1:9999/broken", "timeout": 0.5},
        retry_count=0,
        max_retries=2,
    )
    db.add_all([wf, job, task])
    db.commit()
    task_id = str(task.id)
    job_id = job.id
    db.close()

    from contextlib import contextmanager

    @contextmanager
    def mock_worker_db():
        session = TestingSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Attempt 1 (retry_count 0 -> 1 < max_retries 2): should set RETRYING and call apply_async
    with patch("tasks.execute_task.get_worker_db", mock_worker_db), patch("tasks.execute_task.execute_task.apply_async") as mock_apply:
        result = execute_task(task_id)
        assert result["status"] == "retrying"
        assert result["retry_count"] == "1"
        mock_apply.assert_called_once()
        _, kwargs = mock_apply.call_args
        assert "countdown" in kwargs
        assert kwargs["countdown"] >= 0

    # Verify task is RETRYING and job is STILL RUNNING
    db2 = TestingSessionLocal()
    t = db2.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
    j = db2.query(Job).filter(Job.id == job_id).first()
    assert t.status == TaskStatus.RETRYING
    assert t.retry_count == 1
    assert j.status == JobStatus.RUNNING
    db2.close()

    # Retry 1 (retry_count 1 -> 2 <= max_retries 2): should set RETRYING again
    with patch("tasks.execute_task.get_worker_db", mock_worker_db), patch("tasks.execute_task.execute_task.apply_async") as mock_apply:
        result2 = execute_task(task_id)
        assert result2["status"] == "retrying"
        assert result2["retry_count"] == "2"
        mock_apply.assert_called_once()

    # Retry 2 (retry_count 2 >= max_retries 2): retries exhausted! Should set FAILED, create DeadLetter, and mark job FAILED
    with patch("tasks.execute_task.get_worker_db", mock_worker_db), patch("tasks.execute_task.execute_task.apply_async") as mock_apply:
        result3 = execute_task(task_id)
        assert result3["status"] == "failed"
        mock_apply.assert_not_called()

    db3 = TestingSessionLocal()
    t_final = db3.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
    j_final = db3.query(Job).filter(Job.id == job_id).first()
    dl_record = db3.query(DeadLetterTask).filter(DeadLetterTask.task_id == uuid.UUID(task_id)).first()

    assert t_final.status == TaskStatus.FAILED
    assert t_final.retry_count == 2
    assert j_final.status == JobStatus.FAILED
    assert dl_record is not None
    assert dl_record.retry_count == 2
    assert dl_record.task_type == "http_call"
    db3.close()
