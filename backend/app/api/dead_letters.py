import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.celery_client import dispatch_task
from app.core.db import get_db
from app.core.deps import require_role
from app.models.dead_letter import DeadLetterTask
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.schemas.dead_letter import DeadLetterRead

router = APIRouter()


@router.get(
    "",
    response_model=list[DeadLetterRead],
    summary="List all dead-lettered tasks (Admin only)",
    tags=["Dead Letters"],
)
def list_dead_letters(
    workflow_id: Optional[uuid.UUID] = Query(None, description="Filter by workflow UUID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> list[DeadLetterTask]:
    """Retrieves all dead-letter tasks. Filterable by workflow_id."""
    query = db.query(DeadLetterTask)
    if workflow_id is not None:
        query = query.filter(DeadLetterTask.workflow_id == str(workflow_id))
    return query.order_by(DeadLetterTask.failed_at.desc()).all()


@router.get(
    "/{dead_letter_id}",
    response_model=DeadLetterRead,
    summary="Get dead-letter task detail (Admin only)",
    tags=["Dead Letters"],
)
def get_dead_letter(
    dead_letter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> DeadLetterTask:
    """Retrieves full details of a single dead-letter record."""
    dl = db.query(DeadLetterTask).filter(DeadLetterTask.id == str(dead_letter_id)).first()
    if not dl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dead-letter record not found",
        )
    return dl


@router.post(
    "/{dead_letter_id}/requeue",
    response_model=DeadLetterRead,
    status_code=status.HTTP_200_OK,
    summary="Requeue a dead-lettered task (Admin only)",
    tags=["Dead Letters"],
)
def requeue_dead_letter(
    dead_letter_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> DeadLetterTask:
    """Resets the original task state, marks requeued_at on the dead-letter record, and dispatches execution fresh."""
    dl = db.query(DeadLetterTask).filter(DeadLetterTask.id == str(dead_letter_id)).first()
    if not dl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dead-letter record not found",
        )

    task = db.query(Task).filter(Task.id == uuid.UUID(dl.task_id)).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated task record no longer exists",
        )

    # 1. Reset original task
    task.status = TaskStatus.PENDING
    task.retry_count = 0
    task.error_message = None
    task.started_at = None
    task.completed_at = None

    # 2. Re-open parent job if it was failed
    job = db.query(Job).filter(Job.id == task.job_id).first()
    if job and job.status == JobStatus.FAILED:
        job.status = JobStatus.RUNNING
        job.completed_at = None

    # 3. Mark dead letter as requeued for history
    dl.requeued_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dl)

    # 4. Dispatch task fresh via Celery preserving job priority queue
    from app.core.queue_routing import get_queue_for_priority

    queue = get_queue_for_priority(job.priority if job else 5)
    dispatch_task("execute_task", args=[str(task.id)], queue=queue)

    return dl
