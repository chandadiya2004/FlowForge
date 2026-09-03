import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole

SAMPLE_DEFINITION = [{"name": "Step 1", "type": "log_message", "config": {"message": "Hello"}}]


def test_create_workflow_success(client: TestClient, member_token: str):
    payload = {
        "name": "Data Pipeline",
        "description": "ETL pipeline",
        "definition": [
            {"name": "Step 1", "type": "log_message", "config": {"message": "Starting"}},
            {"name": "Step 2", "type": "sleep", "config": {"seconds": 1}},
        ],
    }
    res = client.post("/workflows", json=payload, headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Data Pipeline"
    assert len(data["definition"]) == 2
    assert data["is_active"] is True
    assert "id" in data


def test_create_workflow_empty_definition_rejected(client: TestClient, member_token: str):
    payload = {
        "name": "Empty WF",
        "definition": [],
    }
    res = client.post("/workflows", json=payload, headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 422


def test_get_workflow_by_id(client: TestClient, member_token: str):
    create_res = client.post(
        "/workflows",
        json={"name": "Fetch Test", "definition": SAMPLE_DEFINITION},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert create_res.status_code == 201
    wf_id = create_res.json()["id"]

    get_res = client.get(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {member_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["id"] == wf_id
    assert get_res.json()["name"] == "Fetch Test"


def test_list_workflows(client: TestClient, member_token: str):
    client.post(
        "/workflows",
        json={"name": "WF A", "definition": SAMPLE_DEFINITION},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    client.post(
        "/workflows",
        json={"name": "WF B", "definition": SAMPLE_DEFINITION},
        headers={"Authorization": f"Bearer {member_token}"},
    )

    res = client.get("/workflows", headers={"Authorization": f"Bearer {member_token}"})
    assert res.status_code == 200
    names = [w["name"] for w in res.json()]
    assert "WF A" in names
    assert "WF B" in names


def test_update_workflow(client: TestClient, member_token: str):
    create_res = client.post(
        "/workflows",
        json={"name": "Original Name", "description": "Original", "definition": SAMPLE_DEFINITION},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert create_res.status_code == 201
    wf_id = create_res.json()["id"]

    update_res = client.put(
        f"/workflows/{wf_id}",
        json={"name": "Updated Name", "description": "Updated"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Name"
    assert update_res.json()["description"] == "Updated"


def test_delete_workflow(client: TestClient, member_token: str):
    create_res = client.post(
        "/workflows",
        json={"name": "To Delete", "definition": SAMPLE_DEFINITION},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert create_res.status_code == 201
    wf_id = create_res.json()["id"]

    del_res = client.delete(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {member_token}"})
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ok"

    # Verify deactivated
    get_res = client.get(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {member_token}"})
    assert get_res.status_code == 200
    assert get_res.json()["is_active"] is False


def test_workflow_ownership_enforcement(client: TestClient, member_token: str, admin_token: str, db_session: Session):
    # Member 1 creates a workflow
    create_res = client.post(
        "/workflows",
        json={"name": "Member 1 Private WF", "definition": SAMPLE_DEFINITION},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert create_res.status_code == 201
    wf_id = create_res.json()["id"]

    # Member 2 is created
    other_member = User(
        id=uuid.uuid4(),
        email="other_member@flowforge.dev",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.MEMBER,
        is_active=True,
    )
    db_session.add(other_member)
    db_session.commit()
    other_token = create_access_token(data={"sub": str(other_member.id), "role": "member"})

    # Member 2 tries to update Member 1's workflow -> 403 Forbidden
    unauth_update = client.put(
        f"/workflows/{wf_id}",
        json={"name": "Hacked Name"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert unauth_update.status_code == 403

    # Member 2 tries to delete Member 1's workflow -> 403 Forbidden
    unauth_delete = client.delete(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert unauth_delete.status_code == 403

    # Admin CAN update Member 1's workflow -> 200 OK
    admin_update = client.put(
        f"/workflows/{wf_id}",
        json={"name": "Admin Updated Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_update.status_code == 200
    assert admin_update.json()["name"] == "Admin Updated Name"

    # Admin CAN delete Member 1's workflow -> 200 OK (soft-deactivation)
    admin_delete = client.delete(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_delete.status_code == 200
    assert admin_delete.json()["status"] == "ok"

    get_admin_res = client.get(f"/workflows/{wf_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_admin_res.status_code == 200
    assert get_admin_res.json()["is_active"] is False
