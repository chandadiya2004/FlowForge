import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TaskDefinition(BaseModel):
    name: str = Field(..., min_length=1, description="Task step name")
    type: str = Field(..., min_length=1, description="Task step type")
    config: dict[str, Any] = Field(default_factory=dict, description="Task step configuration dictionary")


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    definition: list[TaskDefinition]

    @field_validator("definition")
    @classmethod
    def validate_definition_not_empty(cls, v: list[TaskDefinition]) -> list[TaskDefinition]:
        if not v or len(v) == 0:
            raise ValueError("Workflow definition must contain at least one task definition.")
        return v


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    definition: Optional[list[TaskDefinition]] = None
    is_active: Optional[bool] = None

    @field_validator("definition")
    @classmethod
    def validate_definition_if_provided(cls, v: Optional[list[TaskDefinition]]) -> Optional[list[TaskDefinition]]:
        if v is not None and len(v) == 0:
            raise ValueError("Workflow definition, if provided, must contain at least one task definition.")
        return v


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str]
    owner_id: uuid.UUID
    definition: list[TaskDefinition]
    is_active: bool
    created_at: datetime
    updated_at: datetime
