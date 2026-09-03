import time
from celery import shared_task


@shared_task(name="ping")
def ping() -> str:
    """Throwaway verification task for Milestone 4.
    
    Simulates ~1 second of work and returns 'pong'.
    """
    time.sleep(1)
    return "pong"
