import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ensure backend path is in sys.path to import config and models directly
worker_path = Path(__file__).resolve().parent
backend_path = worker_path.parent / "backend"

for path_str in [str(worker_path), str(backend_path)]:
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.core.config import settings
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.workflow import Workflow

connect_args = {}
engine_kwargs = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_worker_db() -> Generator[Session, None, None]:
    """Context manager providing a transactional database session for worker operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
