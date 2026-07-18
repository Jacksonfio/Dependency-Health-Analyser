import logging
from datetime import datetime, timedelta

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.models import Scan
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task
def cleanup_old_scans(retention_days: int = 30):
    import asyncio
    asyncio.run(_cleanup_old_scans(retention_days))


async def _cleanup_old_scans(retention_days: int = 30):
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    async with async_session_maker() as db:
        try:
            result = await db.execute(
                delete(Scan).where(Scan.started_at < cutoff)
            )
            await db.commit()
            logger.info(f"Cleaned up {result.rowcount} scans older than {retention_days} days")
        except Exception as e:
            logger.error(f"Failed to clean up old scans: {e}")
            raise
