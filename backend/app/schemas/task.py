import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    name: str
    type: str
    sequence: int
    status: str
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    error_message: Optional[str] = None
    retry_count: int
    max_retries: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
