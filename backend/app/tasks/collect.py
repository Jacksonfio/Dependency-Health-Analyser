import logging

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.models import Ecosystem
from app.services.collectors.manager import CollectorManager
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task
def collect_all_vulnerabilities():
    import asyncio
    asyncio.run(_collect_all_vulnerabilities())


async def _collect_all_vulnerabilities():
    async with async_session_maker() as db:
        collector = CollectorManager(db)
        for ecosystem in (Ecosystem.NPM, Ecosystem.PYPI, Ecosystem.MAVEN):
            try:
                await collector.collect_ecosystem_vulnerabilities(ecosystem)
                logger.info(f"Collected vulnerabilities for {ecosystem.value}")
            except Exception as e:
                logger.error(f"Failed to collect vulns for {ecosystem.value}: {e}")


@celery_app.task(bind=True, max_retries=3)
def collect_package_task(self, ecosystem: str, name: str):
    import asyncio
    asyncio.run(_collect_package(ecosystem, name))


async def _collect_package(ecosystem: str, name: str):
    async with async_session_maker() as db:
        collector = CollectorManager(db)
        try:
            await collector.collect_package(Ecosystem(ecosystem), name)
            await db.commit()
            logger.info(f"Collected package {ecosystem}/{name}")
        except Exception as e:
            logger.error(f"Failed to collect package {ecosystem}/{name}: {e}")
            raise
