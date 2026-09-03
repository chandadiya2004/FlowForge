import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class DeadLetterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    job_id: uuid.UUID
    workflow_id: uuid.UUID
    task_type: str
    input_data: Optional[Any] = None
    error_message: Optional[str] = None
    retry_count: int
    failed_at: datetime
    requeued_at: Optional[datetime] = None
