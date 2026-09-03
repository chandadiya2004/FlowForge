from typing import Any, Optional
from fastapi import APIRouter, status
from pydantic import BaseModel

from app.core.celery_client import dispatch_task, get_task_result

# ==============================================================================
# TEMPORARY / DEBUG-ONLY ROUTES: Milestone 4 Plumbing Verification
# These endpoints exist solely to verify Redis broker & Celery worker connectivity.
# Remove once Milestone 5 real job execution pipelines are implemented.
# ==============================================================================

router = APIRouter()


class TaskDispatchResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[Any] = None


@router.post(
    "/ping-worker",
    response_model=TaskDispatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="[TEMPORARY] Dispatch ping verification task to Celery",
)
def ping_worker() -> TaskDispatchResponse:
    """Dispatches the throwaway 'ping' task to Celery via Redis broker.
    
    Returns immediately with task_id without blocking.
    """
    async_result = dispatch_task("ping")
    return TaskDispatchResponse(
        task_id=async_result.id,
        status="dispatched",
    )


@router.get(
    "/task-result/{task_id}",
    response_model=TaskStatusResponse,
    summary="[TEMPORARY] Check state and output of dispatched Celery task",
)
def check_task_result(task_id: str) -> TaskStatusResponse:
    """Queries Celery result backend for task state (PENDING, STARTED, SUCCESS, FAILURE)."""
    async_result = get_task_result(task_id)

    task_status = async_result.status
    task_result = None

    if async_result.ready():
        if async_result.successful():
            task_result = async_result.result
        else:
            task_result = str(async_result.result)

    return TaskStatusResponse(
        task_id=task_id,
        status=task_status,
        result=task_result,
    )
