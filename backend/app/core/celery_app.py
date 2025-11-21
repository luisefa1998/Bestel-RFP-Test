"""
Celery configuration for task queue.
"""
from celery import Celery
from celery.signals import worker_process_init
import os

# Create Celery app
celery_app = Celery(
    "document_ai",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_default_queue=os.getenv("CELERY_QUEUE_NAME", "celery"),
)

# Set up logging when Celery worker starts
@worker_process_init.connect
def setup_celery_logging(**kwargs):
    """Initialize logging configuration for Celery worker processes"""
    from app.core.logging_config import setup_logging
    from app.core.settings import settings
    setup_logging(mode=settings.LOGGING_MODE)

# Import tasks to ensure they're registered
celery_app.autodiscover_tasks(["app.tasks"])

# Made with Bob
