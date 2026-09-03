import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from main import app

# In-memory SQLite for lightning-fast, zero-dependency testing
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_register_user_success():
    payload = {"email": "member@example.com", "password": "securepassword123"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "member@example.com"
    assert data["role"] == "member"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email():
    payload = {"email": "duplicate@example.com", "password": "securepassword123"}
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    # Attempt to register identical email
    dup_response = client.post("/auth/register", json=payload)
    assert dup_response.status_code == 409
    assert "already exists" in dup_response.json()["detail"]


def test_login_success():
    client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "mypassword456"},
    )
    login_response = client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "mypassword456"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"


def test_login_invalid_password():
    client.post(
        "/auth/register",
        json={"email": "wrongpwd@example.com", "password": "correct_password"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "wrongpwd@example.com", "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_get_me_success():
    client.post(
        "/auth/register",
        json={"email": "me@example.com", "password": "mypassword456"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "me@example.com", "password": "mypassword456"},
    )
    token = login_res.json()["access_token"]

    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "me@example.com"
    assert me_res.json()["role"] == "member"


def test_get_me_unauthorized_without_token():
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_refresh_token_exchange():
    client.post(
        "/auth/register",
        json={"email": "refresh@example.com", "password": "mypassword456"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "refresh@example.com", "password": "mypassword456"},
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
    assert me_res.json()["email"] == "refresh@example.com"


def test_admin_check_forbidden_for_member():
    client.post(
        "/auth/register",
        json={"email": "regular@example.com", "password": "mypassword456"},
    )
    login_res = client.post(
        "/auth/login",
        json={"email": "regular@example.com", "password": "mypassword456"},
    )
    token = login_res.json()["access_token"]

    admin_res = client.get("/admin-check", headers={"Authorization": f"Bearer {token}"})
    assert admin_res.status_code == 403
    assert "Operation not permitted" in admin_res.json()["detail"]


def test_admin_check_allowed_for_admin():
    db = TestingSessionLocal()
    admin_user = User(
        email="admin@example.com",
        hashed_password=get_password_hash("adminsecret"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    db.close()

    login_res = client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "adminsecret"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    admin_res = client.get("/admin-check", headers={"Authorization": f"Bearer {token}"})
    assert admin_res.status_code == 200
    assert admin_res.json()["status"] == "ok"
    assert admin_res.json()["role"] == "admin"
    assert admin_res.json()["email"] == "admin@example.com"
