import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Uuid
from sqlalchemy.orm import relationship

from app.core.db import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    workflow_id = Column(Uuid(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_by = Column(Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(
        Enum(JobStatus, name="job_status", values_callable=lambda obj: [e.value for e in obj]),
        default=JobStatus.PENDING,
        nullable=False,
        index=True,
    )
    priority = Column(Integer, default=5, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    workflow = relationship("Workflow", back_populates="jobs")
    user = relationship("User", backref="jobs")
    tasks = relationship("Task", back_populates="job", cascade="all, delete-orphan", order_by="Task.sequence")

    def __repr__(self) -> str:
        return f"<Job {self.id} (status={self.status}, workflow_id={self.workflow_id})>"
