import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.models.workflow import Workflow
from main import app
from tests.conftest import TestingSessionLocal

client = TestClient(app)



def create_user_and_token(email: str, role: UserRole = UserRole.MEMBER) -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=get_password_hash("password123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()

    role_str = role.value if hasattr(role, "value") else str(role)
    token = create_access_token(data={"sub": str(user.id), "role": role_str})
    return user, token


def test_create_workflow_success():
    _, token = create_user_and_token("alice@example.com")
    payload = {
        "name": "ETL Pipeline",
        "description": "Extract, transform and load data",
        "definition": [
            {"name": "Extract", "type": "extractor", "config": {"source": "s3://bucket/data.csv"}},
            {"name": "Transform", "type": "transformer", "config": {"delimiter": ","}},
        ],
    }
    res = client.post("/workflows", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "ETL Pipeline"
    assert data["is_active"] is True
    assert len(data["definition"]) == 2
    assert data["definition"][0]["name"] == "Extract"
    assert data["definition"][1]["name"] == "Transform"


def test_create_workflow_empty_definition_rejected():
    _, token = create_user_and_token("alice2@example.com")
    payload = {
        "name": "Invalid Workflow",
        "description": "No tasks",
        "definition": [],
    }
    res = client.post("/workflows", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 422


def test_list_workflows_ownership_isolation():
    user1, token1 = create_user_and_token("user1@example.com")
    user2, token2 = create_user_and_token("user2@example.com")
    _, admin_token = create_user_and_token("admin@example.com", role=UserRole.ADMIN)

    # User 1 creates a workflow
    client.post(
        "/workflows",
        json={"name": "User1 Flow", "definition": [{"name": "Step 1", "type": "job", "config": {}}]},
        headers={"Authorization": f"Bearer {token1}"},
    )
    # User 2 creates a workflow
    client.post(
        "/workflows",
        json={"name": "User2 Flow", "definition": [{"name": "Step 1", "type": "job", "config": {}}]},
        headers={"Authorization": f"Bearer {token2}"},
    )

    # User 1 lists workflows (should only see User 1's workflow)
    res1 = client.get("/workflows", headers={"Authorization": f"Bearer {token1}"})
    assert res1.status_code == 200
    assert len(res1.json()) == 1
    assert res1.json()[0]["name"] == "User1 Flow"

    # Admin lists workflows (should see both)
    res_admin = client.get("/workflows", headers={"Authorization": f"Bearer {admin_token}"})
    assert res_admin.status_code == 200
    assert len(res_admin.json()) == 2


def test_get_and_update_and_soft_delete_workflow():
    _, token = create_user_and_token("owner@example.com")
    _, other_token = create_user_and_token("other@example.com")

    # Create workflow
    create_res = client.post(
        "/workflows",
        json={"name": "My Flow", "definition": [{"name": "Step 1", "type": "task", "config": {}}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    wf_id = create_res.json()["id"]

    # Other user cannot get it
    res_forbidden = client.get(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res_forbidden.status_code == 403

    # Owner can get it
    res_owner = client.get(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == wf_id

    # Owner updates it
    res_update = client.put(
        f"/workflows/{wf_id}",
        json={"name": "Updated Flow Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["name"] == "Updated Flow Name"

    # Owner soft deletes it
    res_del = client.delete(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_del.status_code == 200

    # Verify is_active is now False
    res_check = client.get(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {token}"})
    assert res_check.status_code == 200
    assert res_check.json()["is_active"] is False


def test_create_job_unpacks_tasks_in_order():
    _, token = create_user_and_token("runner@example.com")

    # Create 3-step workflow
    wf_payload = {
        "name": "Multi-Step Pipeline",
        "definition": [
            {"name": "Download", "type": "http_get", "config": {"url": "https://data.com"}},
            {"name": "Parse", "type": "json_parser", "config": {"strict": True}},
            {"name": "Store", "type": "db_insert", "config": {"table": "records"}},
        ],
    }
    wf_res = client.post("/workflows", json=wf_payload, headers={"Authorization": f"Bearer {token}"})
    wf_id = wf_res.json()["id"]

    # Trigger job creation
    job_res = client.post(f"/workflows/{wf_id}/jobs", headers={"Authorization": f"Bearer {token}"})
    assert job_res.status_code == 201
    job_data = job_res.json()
    assert job_data["status"] == "pending"
    assert job_data["workflow_id"] == wf_id
    assert "tasks" in job_data
    assert len(job_data["tasks"]) == 3

    # Verify task ordering and pending statuses
    tasks = job_data["tasks"]
    assert tasks[0]["name"] == "Download"
    assert tasks[0]["sequence"] == 1
    assert tasks[0]["status"] == "pending"
    assert tasks[0]["input_data"] == {"url": "https://data.com"}

    assert tasks[1]["name"] == "Parse"
    assert tasks[1]["sequence"] == 2
    assert tasks[1]["status"] == "pending"

    assert tasks[2]["name"] == "Store"
    assert tasks[2]["sequence"] == 3
    assert tasks[2]["status"] == "pending"

    # Test GET /jobs/{id}
    job_id = job_data["id"]
    get_job_res = client.get(f"/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
    assert get_job_res.status_code == 200
    assert len(get_job_res.json()["tasks"]) == 3

    # Test GET /jobs/{id}/tasks
    tasks_res = client.get(f"/jobs/{job_id}/tasks", headers={"Authorization": f"Bearer {token}"})
    assert tasks_res.status_code == 200
    task_list = tasks_res.json()
    assert len(task_list) == 3
    assert [t["sequence"] for t in task_list] == [1, 2, 3]


def test_list_jobs_with_status_filter():
    user, token = create_user_and_token("filter_user@example.com")
    db = TestingSessionLocal()

    # Create dummy workflow
    wf = Workflow(
        name="Test Flow",
        owner_id=user.id,
        definition=[{"name": "step", "type": "type", "config": {}}],
        is_active=True,
    )
    db.add(wf)
    db.commit()

    # Create one pending and one running job
    job1 = Job(workflow_id=wf.id, triggered_by=user.id, status=JobStatus.PENDING)
    job2 = Job(workflow_id=wf.id, triggered_by=user.id, status=JobStatus.RUNNING)
    db.add_all([job1, job2])
    db.commit()
    db.close()

    # List all
    res_all = client.get("/jobs", headers={"Authorization": f"Bearer {token}"})
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2
    # Ensure lightweight (no nested tasks key in list endpoint)
    assert "tasks" not in res_all.json()[0]

    # Filter by pending
    res_pending = client.get("/jobs?status=pending", headers={"Authorization": f"Bearer {token}"})
    assert res_pending.status_code == 200
    assert len(res_pending.json()) == 1
    assert res_pending.json()[0]["status"] == "pending"


def test_cannot_create_job_from_inactive_workflow():
    _, token = create_user_and_token("user_inactive@example.com")

    # Create workflow and delete it
    create_res = client.post(
        "/workflows",
        json={"name": "Flow to Delete", "definition": [{"name": "step1", "type": "task", "config": {}}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    wf_id = create_res.json()["id"]
    client.delete(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {token}"})

    # Attempt to trigger job on deactivated workflow
    job_res = client.post(f"/workflows/{wf_id}/jobs", headers={"Authorization": f"Bearer {token}"})
    assert job_res.status_code == 400
    assert "inactive" in job_res.json()["detail"]
