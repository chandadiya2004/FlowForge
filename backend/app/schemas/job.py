import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.task import TaskRead


class JobCreate(BaseModel):
    priority: Optional[int] = Field(
        default=5,
        ge=1,
        le=10,
        description="Job priority between 1 (highest) and 10 (lowest). Default: 5",
    )


class JobPriorityUpdate(BaseModel):
    priority: int = Field(
        ...,
        ge=1,
        le=10,
        description="New job priority between 1 (highest) and 10 (lowest)",
    )


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    triggered_by: uuid.UUID
    status: str
    priority: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobDetailRead(JobRead):
    tasks: list[TaskRead] = []
