"""Test Configuration and Shared Fixtures for FlowForge Test Suite (Milestone 10).

Database Architecture Choice:
An isolated SQLite in-memory database ("sqlite:///:memory:") with StaticPool and
check_same_thread=False is selected for the automated test suite.
Rationale:
1. Speed & Determinism: Runs in-memory in under 15 seconds across all 35+ tests.
2. Portability: Allows zero-setup test runs on developer workstations without running external daemons.
3. Hermetic Isolation: Each test session creates fresh tables via Base.metadata.create_all
   and drops all tables on teardown.
"""

import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure worker and backend roots are on sys.path
backend_path = Path(__file__).resolve().parent.parent
worker_path = backend_path.parent / "worker"
for p in [str(backend_path), str(worker_path)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from app.core.db import Base, get_db
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from main import app

# Configure in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Configure Celery in synchronous eager mode for hermetic in-process testing
from celery_app import celery_app
import app.core.celery_client as celery_client_module

celery_app.set_default()
celery_app.set_current()
celery_app.conf.update(
    task_always_eager=True,
    task_eager_propagates=True,
)
celery_client_module.celery_client = celery_app

# Route worker database operations to the test session
import db as worker_db_module

worker_db_module.SessionLocal = TestingSessionLocal

if "tasks.execute_task" in sys.modules:
    sys.modules["tasks.execute_task"].get_worker_db = worker_db_module.get_worker_db


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    """Initializes tables before each test and drops them on completion."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provides a standalone test DB session for test setup and verification."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> TestClient:
    """Provides a FastAPI test client wired to the in-memory database."""
    return TestClient(app)


@pytest.fixture
def member_user(db_session: Session) -> User:
    """Creates a regular member user."""
    user = User(
        id=uuid.uuid4(),
        email="member@flowforge.dev",
        hashed_password=get_password_hash("MemberPass123!"),
        role=UserRole.MEMBER,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def member_token(member_user: User) -> str:
    """Generates a valid JWT access token for the member user."""
    return create_access_token(data={"sub": str(member_user.id), "role": member_user.role.value})


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Creates an administrator user."""
    user = User(
        id=uuid.uuid4(),
        email="admin@flowforge.dev",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generates a valid JWT access token for the admin user."""
    return create_access_token(data={"sub": str(admin_user.id), "role": admin_user.role.value})


@pytest.fixture
def mock_http():
    """Mocks outbound HTTP calls via respx to ensure tests never make external network requests."""
    with respx.mock(assert_all_called=False) as respx_mock:
        yield respx_mock
