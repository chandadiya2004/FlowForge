import logging
import uuid
from datetime import datetime, timezone
from celery import shared_task

from db import get_worker_db
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from tasks.orchestrate import handle_task_completion
from tasks.registry import get_handler

logger = logging.getLogger("flowforge.worker.execute")
logger.setLevel(logging.INFO)


@shared_task(name="execute_task")
def execute_task(task_id: str) -> dict[str, str]:
    """Executes a single task, updates its database state in real-time, and triggers next steps."""
    logger.info("Received execute_task for task_id=%s", task_id)
    task_uuid = uuid.UUID(task_id)

    with get_worker_db() as db:
        task = db.query(Task).filter(Task.id == task_uuid).first()
        if not task:
            logger.error("Task %s not found in database", task_id)
            return {"status": "error", "message": "Task not found"}

        job = db.query(Job).filter(Job.id == task.job_id).first()

        now = datetime.now(timezone.utc)

        # 1. If job is still pending, mark it running
        if job and job.status == JobStatus.PENDING:
            job.status = JobStatus.RUNNING
            job.started_at = now

        # 2. Mark current task running and record started_at
        task.status = TaskStatus.RUNNING
        task.started_at = now
        db.commit()

        # 3. Execute handler according to task.type
        try:
            handler = get_handler(task.type)
            input_data = task.input_data if isinstance(task.input_data, dict) else {}
            output = handler(input_data)
            task.output_data = output
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc)
            logger.info("Task %s completed successfully", task_id)
        except Exception as exc:
            task.error_message = str(exc)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            logger.warning("Task %s failed: %s", task_id, exc)

        db.commit()

        # 4. Orchestrate next task or finalize job
        handle_task_completion(task.id, db)

    return {"status": "processed", "task_id": task_id}
