import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import relationship

from app.core.db import Base

JSONType = SQLiteJSON().with_variant(JSONB, "postgresql")


class DeadLetterTask(Base):
    __tablename__ = "dead_letter_tasks"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    task_id = Column(
        String(36),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    job_id = Column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_id = Column(
        String(36),
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type = Column(String(100), nullable=False)
    input_data = Column(JSONType, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    failed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    requeued_at = Column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Relationships
    task = relationship("Task", backref="dead_letters")
    job = relationship("Job", backref="dead_letters")
    workflow = relationship("Workflow", backref="dead_letters")

    def __repr__(self) -> str:
        return f"<DeadLetterTask id={self.id} task_id={self.task_id} job_id={self.job_id} retries={self.retry_count}>"
