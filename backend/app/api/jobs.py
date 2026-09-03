import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.models.user import User, UserRole
from app.models.workflow import Workflow
from app.schemas.job import JobDetailRead, JobRead
from app.schemas.task import TaskRead

router = APIRouter()


@router.post(
    "/workflows/{workflow_id}/jobs",
    response_model=JobDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job from a workflow",
    tags=["Jobs"],
)
def create_job_for_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Job:
    """Creates a Job in 'pending' status and unpacks workflow definition entries into ordered 'pending' tasks."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    if not workflow.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a job from an inactive/deactivated workflow",
        )

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if workflow.owner_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. You do not own this workflow.",
        )

    # 1. Create Job record
    new_job = Job(
        workflow_id=workflow.id,
        triggered_by=current_user.id,
        status=JobStatus.PENDING,
        priority=5,
    )
    db.add(new_job)
    db.flush()

    # 2. Unpack workflow definition into ordered Task rows
    tasks_to_create = []
    for idx, task_def in enumerate(workflow.definition, start=1):
        task_name = task_def.get("name", f"Step {idx}")
        task_type = task_def.get("type", "standard")
        task_config = task_def.get("config", {})

        task_record = Task(
            job_id=new_job.id,
            name=task_name,
            type=task_type,
            sequence=idx,
            status=TaskStatus.PENDING,
            input_data=task_config,
            retry_count=0,
            max_retries=3,
        )
        tasks_to_create.append(task_record)

    db.add_all(tasks_to_create)
    db.commit()
    db.refresh(new_job)
    return new_job


@router.get(
    "/jobs",
    response_model=list[JobRead],
    summary="List jobs",
    tags=["Jobs"],
)
def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter jobs by status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Job]:
    """List lightweight jobs. Regular users only see their own jobs; admins see all."""
    query = db.query(Job)

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if not is_admin:
        query = query.filter(Job.triggered_by == current_user.id)

    if status_filter:
        query = query.filter(Job.status == status_filter.lower())

    return query.order_by(Job.created_at.desc()).all()


@router.get(
    "/jobs/{job_id}",
    response_model=JobDetailRead,
    summary="Get job details with nested tasks",
    tags=["Jobs"],
)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Job:
    """Get full job detail with nested tasks ordered by sequence. 404 if not found, 403 if unauthorized."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if job.triggered_by != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. You do not own this job.",
        )

    return job


@router.get(
    "/jobs/{job_id}/tasks",
    response_model=list[TaskRead],
    summary="Get tasks for a specific job",
    tags=["Jobs"],
)
def get_job_tasks(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Task]:
    """Get task list for a job, ordered by sequence."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if job.triggered_by != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. You do not own this job.",
        )

    tasks = (
        db.query(Task)
        .filter(Task.job_id == job_id)
        .order_by(Task.sequence.asc())
        .all()
    )
    return tasks
