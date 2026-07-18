from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "dep_health",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.scan",
        "app.tasks.collect",
        "app.tasks.notify",
        "app.tasks.maintenance",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3000,
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=100,
    beat_schedule={
        "scan-monitored-projects": {
            "task": "app.tasks.scan.scan_all_monitored_projects",
            "schedule": 3600.0,
        },
        "collect-vulnerabilities": {
            "task": "app.tasks.collect.collect_all_vulnerabilities",
            "schedule": 7200.0,
        },
        "update-health-scores": {
            "task": "app.tasks.scan.update_all_health_scores",
            "schedule": 1800.0,
        },
        "cleanup-old-scans": {
            "task": "app.tasks.maintenance.cleanup_old_scans",
            "schedule": 86400.0,
        },
    },
)

celery_app.autodiscover_tasks()


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")