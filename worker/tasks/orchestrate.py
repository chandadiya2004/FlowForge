import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus


def handle_task_completion(task_id: uuid.UUID | str, db: Session) -> None:
    """Evaluates task outcome and coordinates the next step in the job lifecycle."""
    if isinstance(task_id, str):
        task_id = uuid.UUID(task_id)

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return

    job = db.query(Job).filter(Job.id == task.job_id).first()
    if not job:
        return

    now = datetime.now(timezone.utc)

    if task.status == TaskStatus.FAILED:
        # Task failed: mark job failed and halt sequence
        job.status = JobStatus.FAILED
        job.completed_at = now
        db.commit()
        return

    if task.status == TaskStatus.COMPLETED:
        # Task succeeded: locate next task in sequence
        next_task = (
            db.query(Task)
            .filter(Task.job_id == job.id, Task.sequence > task.sequence)
            .order_by(Task.sequence.asc())
            .first()
        )

        if next_task:
            # Dispatch next task in pipeline
            from tasks.execute_task import execute_task
            execute_task.delay(str(next_task.id))
        else:
            # All tasks in sequence finished: mark job completed
            job.status = JobStatus.COMPLETED
            job.completed_at = now
            db.commit()
