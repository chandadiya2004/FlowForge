from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.user import User


def test_register_user_success(client: TestClient):
    payload = {"email": "newuser@example.com", "password": "securepassword123"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "member"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient, member_user: User):
    # Attempt to register member_user's email again
    payload = {"email": member_user.email, "password": "anypassword123"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_login_success(client: TestClient, member_user: User):
    login_response = client.post(
        "/auth/login",
        json={"email": member_user.email, "password": "MemberPass123!"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_login_invalid_password(client: TestClient, member_user: User):
    response = client.post(
        "/auth/login",
        json={"email": member_user.email, "password": "wrongpassword!"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_nonexistent_user(client: TestClient):
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpassword!"},
    )
    assert response.status_code == 401


def test_get_me_success(client: TestClient, member_user: User, member_token: str):
    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {member_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == member_user.email
    assert me_res.json()["role"] == "member"


def test_get_me_unauthorized_without_token(client: TestClient):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_invalid_token(client: TestClient):
    response = client.get("/auth/me", headers={"Authorization": "Bearer invalid_garbage_token"})
    assert response.status_code == 401


def test_get_me_expired_token(client: TestClient, member_user: User):
    expired_token = create_access_token(
        data={"sub": str(member_user.id), "role": member_user.role.value},
        expires_delta=timedelta(seconds=-10),
    )
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


def test_refresh_token_exchange(client: TestClient, member_user: User):
    login_res = client.post(
        "/auth/login",
        json={"email": member_user.email, "password": "MemberPass123!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    refresh_res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens

    # Verify new access token works on protected route
    me_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == member_user.email


def test_refresh_token_invalid(client: TestClient):
    refresh_res = client.post("/auth/refresh", json={"refresh_token": "invalid_refresh_token"})
    assert refresh_res.status_code == 401


def test_admin_check_forbidden_for_member(client: TestClient, member_token: str):
    admin_res = client.get("/admin-check", headers={"Authorization": f"Bearer {member_token}"})
    assert admin_res.status_code == 403
    assert "Operation not permitted" in admin_res.json()["detail"]


def test_admin_check_allowed_for_admin(client: TestClient, admin_user: User, admin_token: str):
    admin_res = client.get("/admin-check", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_res.status_code == 200
    assert admin_res.json()["status"] == "ok"
    assert admin_res.json()["role"] == "admin"
    assert admin_res.json()["email"] == admin_user.email
