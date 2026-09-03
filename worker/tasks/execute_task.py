import logging
import uuid
from datetime import datetime, timezone
from celery import shared_task

from db import get_worker_db
from app.core.config import settings
from app.core.queue_routing import get_queue_for_priority
from app.models.dead_letter import DeadLetterTask
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from tasks.orchestrate import handle_task_completion
from tasks.registry import get_handler

logger = logging.getLogger("flowforge.worker.execute")
logger.setLevel(logging.INFO)


@shared_task(name="execute_task")
def execute_task(task_id: str) -> dict[str, str]:
    """Executes a single task, updates database state in real-time, and handles retry/dead-letter or orchestration."""
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
            db.commit()
            logger.info("Task %s completed successfully", task_id)

            # Advance orchestration on success
            handle_task_completion(task.id, db)
            return {"status": "completed", "task_id": task_id}

        except Exception as exc:
            logger.warning("Task %s attempt failed: %s", task_id, exc)
            task.error_message = str(exc)

            # Check if retries are available
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                db.commit()

                # Exponential backoff: base_delay * 2^(retry_count - 1), capped at max_delay
                backoff_factor = 2 ** (task.retry_count - 1)
                delay = min(
                    float(settings.RETRY_BASE_DELAY_SECONDS) * backoff_factor,
                    float(settings.RETRY_MAX_DELAY_SECONDS),
                )
                logger.info(
                    "Task %s scheduled for retry %s/%s in %.1f seconds",
                    task_id,
                    task.retry_count,
                    task.max_retries,
                    delay,
                )

                # Re-dispatch using countdown preserving priority queue; do NOT advance job orchestration
                queue = get_queue_for_priority(job.priority if job else 5)
                execute_task.apply_async(args=[task_id], countdown=max(1, int(delay)), queue=queue)
                return {"status": "retrying", "task_id": task_id, "retry_count": str(task.retry_count)}

            else:
                # Retries exhausted: mark failed permanently
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.now(timezone.utc)

                # Create DeadLetterTask record
                dead_letter = DeadLetterTask(
                    id=uuid.uuid4(),
                    task_id=task.id,
                    job_id=task.job_id,
                    workflow_id=job.workflow_id if job else task.job.workflow_id,
                    task_type=task.type,
                    input_data=task.input_data,
                    error_message=str(exc),
                    retry_count=task.retry_count,
                    failed_at=task.completed_at,
                )
                db.add(dead_letter)
                db.commit()

                logger.warning(
                    "Task %s permanently failed after %s attempts. Created DeadLetterTask %s.",
                    task_id,
                    task.retry_count,
                    dead_letter.id,
                )

                # Proceed with job orchestration to mark job failed and halt sequence
                handle_task_completion(task.id, db)
                return {"status": "failed", "task_id": task_id, "dead_letter_id": str(dead_letter.id)}
