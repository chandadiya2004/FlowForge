from typing import Any, Optional
from celery import Celery
from celery.result import AsyncResult

from app.core.config import settings

# Lightweight Celery instance for task dispatching from FastAPI
celery_client = Celery(
    "flowforge_client",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_client.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
)


def dispatch_task(
    name: str,
    args: Optional[list[Any]] = None,
    kwargs: Optional[dict[str, Any]] = None,
    queue: Optional[str] = None,
    **options: Any,
) -> AsyncResult:
    """Dispatches an asynchronous task by name to Celery without loading worker modules."""
    if queue:
        options["queue"] = queue
    if getattr(celery_client.conf, "task_always_eager", False):
        task = celery_client.tasks.get(name)
        if task:
            return task.apply(args=args or [], kwargs=kwargs or {})
    return celery_client.send_task(name, args=args or [], kwargs=kwargs or {}, **options)


def get_task_result(task_id: str) -> AsyncResult:
    """Retrieves the AsyncResult tracker for the given task ID."""
    return AsyncResult(task_id, app=celery_client)
