import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.models import Alert
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task
def send_pending_alerts():
    import asyncio
    asyncio.run(_send_pending_alerts())


async def _send_pending_alerts():
    async with async_session_maker() as db:
        result = await db.execute(
            select(Alert).where(Alert.is_read == False, Alert.is_dismissed == False)
        )
        alerts = result.scalars().all()
        for alert in alerts:
            try:
                logger.info(f"Alert [{alert.severity}] {alert.title}: {alert.message}")
            except Exception as e:
                logger.error(f"Failed to dispatch alert {alert.id}: {e}")


@celery_app.task(bind=True, max_retries=3)
def notify_alert_task(self, alert_id: str):
    import asyncio
    asyncio.run(_notify_alert(alert_id))


async def _notify_alert(alert_id: str):
    async with async_session_maker() as db:
        alert = await db.get(Alert, alert_id)
        if not alert:
            logger.warning(f"Alert {alert_id} not found")
            return
        logger.info(f"Notifying alert [{alert.severity}] {alert.title}")
