import importlib
import pkgutil
import sys
from pathlib import Path
from celery import Celery

# Add worker and backend directories to sys.path
worker_path = Path(__file__).resolve().parent
backend_path = worker_path.parent / "backend"

for path_str in [str(worker_path), str(backend_path)]:
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from app.core.config import settings

celery_app = Celery(
    "flowforge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_time_limit=300,
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
)

# Autodiscover and import all modules inside worker/tasks/
import tasks
for module_info in pkgutil.iter_modules(tasks.__path__):
    importlib.import_module(f"tasks.{module_info.name}")

if __name__ == "__main__":
    celery_app.start()
