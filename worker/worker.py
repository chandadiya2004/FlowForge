"""Worker entry point stub for FlowForge.

Run via celery CLI:
    celery -A celery_app worker --loglevel=info
Or directly execute this script:
    python worker.py
"""

from celery_app import celery_app

def main() -> None:
    print("Starting FlowForge Celery Worker...")
    celery_app.worker_main(["worker", "--loglevel=info"])

if __name__ == "__main__":
    main()
