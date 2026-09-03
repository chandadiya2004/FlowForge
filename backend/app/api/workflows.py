import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.workflow import Workflow
from app.schemas.job import JobDetailRead
from app.schemas.workflow import WorkflowCreate, WorkflowRead, WorkflowUpdate

router = APIRouter()


@router.post(
    "",
    response_model=WorkflowRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new workflow",
)
def create_workflow(
    workflow_in: WorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workflow:
    """Create a new workflow with definition task steps owned by the authenticated user."""
    # Convert Pydantic models in definition list to serializable dicts
    definition_data = [task.model_dump() for task in workflow_in.definition]

    workflow = Workflow(
        name=workflow_in.name,
        description=workflow_in.description,
        owner_id=current_user.id,
        definition=definition_data,
        is_active=True,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get(
    "",
    response_model=list[WorkflowRead],
    summary="List workflows",
)
def list_workflows(
    include_inactive: bool = Query(False, description="Include soft-deleted/inactive workflows"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Workflow]:
    """List workflows. Regular users only see their own workflows; admins see all."""
    query = db.query(Workflow)

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if not is_admin:
        query = query.filter(Workflow.owner_id == current_user.id)

    if not include_inactive:
        query = query.filter(Workflow.is_active == True)  # noqa: E712

    return query.order_by(Workflow.created_at.desc()).all()


@router.post(
    "/{workflow_id}/jobs",
    response_model=JobDetailRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job from a workflow",
)
def create_job_for_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a Job in 'pending' status and unpacks workflow definition entries into ordered 'pending' tasks."""
    from app.api.jobs import create_job_for_workflow as _create_job
    return _create_job(workflow_id=workflow_id, db=db, current_user=current_user)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowRead,
    summary="Get workflow details",
)
def get_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workflow:
    """Get workflow by ID. 404 if not found, 403 if not owner and not admin."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if workflow.owner_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. You do not own this workflow.",
        )

    return workflow


@router.put(
    "/{workflow_id}",
    response_model=WorkflowRead,
    summary="Update a workflow",
)
def update_workflow(
    workflow_id: uuid.UUID,
    workflow_in: WorkflowUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Workflow:
    """Update workflow by ID. Owner or admin only."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if workflow.owner_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. You do not own this workflow.",
        )

    update_data = workflow_in.model_dump(exclude_unset=True)
    if "definition" in update_data and update_data["definition"] is not None:
        update_data["definition"] = [task.model_dump() for task in workflow_in.definition]

    for field, value in update_data.items():
        setattr(workflow, field, value)

    db.commit()
    db.refresh(workflow)
    return workflow


@router.delete(
    "/{workflow_id}",
    summary="Soft delete a workflow",
)
def delete_workflow(
    workflow_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Soft delete workflow via is_active = False. Owner or admin only."""
    workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found",
        )

    is_admin = current_user.role == UserRole.ADMIN or str(current_user.role) == "admin"
    if workflow.owner_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted. You do not own this workflow.",
        )

    workflow.is_active = False
    db.commit()
    return {"status": "ok", "message": "Workflow deactivated successfully."}
