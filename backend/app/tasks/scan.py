import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, func, and_, or_
from app.core.config import get_settings
from app.db.models import Project, Scan, ProjectDependency, Vulnerability, ProjectDependencyVulnerability, Severity
from app.services.collectors.manager import CollectorManager
from app.services.scoring.engine import ScoringEngine
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

DATABASE_URL = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)
def scan_project_task(self, project_id: str, scan_id: str = None):
    import asyncio
    asyncio.run(_scan_project(project_id, scan_id))


async def _scan_project(project_id: str, scan_id: str = None):
    async with async_session_maker() as db:
        project = await db.get(Project, project_id)
        if not project:
            logger.error(f"Project {project_id} not found")
            return
        
        if not scan_id:
            scan = Scan(project_id=project_id, scan_type="full", status="running")
            db.add(scan)
            await db.flush()
            scan_id = scan.id
        else:
            scan = await db.get(Scan, scan_id)
            if not scan:
                logger.error(f"Scan {scan_id} not found")
                return
            scan.status = "running"
        
        try:
            collector = CollectorManager(db)
            
            for dep in project.dependencies:
                if dep.package_id:
                    await collector.refresh_package(dep.package_id)
            
            await db.flush()
            
            scan.status = "completed"
            scan.completed_at = datetime.utcnow()
            scan.total_dependencies = len(project.dependencies) if project.dependencies else 0
            
            project.last_scanned_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info(f"Scan completed for project {project_id}")
            
        except Exception as e:
            logger.error(f"Scan failed for project {project_id}: {e}")
            if scan:
                scan.status = "failed"
                scan.error = str(e)
                scan.completed_at = datetime.utcnow()
            await db.commit()
            raise


@celery_app.task
def scan_all_monitored_projects():
    import asyncio
    asyncio.run(_scan_all_monitored_projects())


async def _scan_all_monitored_projects():
    async with async_session_maker() as db:
        result = await db.execute(select(Project).where(Project.is_monitored == True))
        projects = result.scalars().all()
        for project in projects:
            scan_project_task.delay(str(project.id))


@celery_app.task
def update_all_health_scores():
    import asyncio
    asyncio.run(_update_all_health_scores())


async def _update_all_health_scores():
    async with async_session_maker() as db:
        result = await db.execute(select(Project).where(Project.is_monitored == True))
        projects = result.scalars().all()
        engine = ScoringEngine(db)
        for project in projects:
            try:
                await engine.generate_project_health_report(str(project.id))
            except Exception as e:
                logger.error(f"Failed to update health for project {project.id}: {e}")


@celery_app.task
def collect_all_vulnerabilities():
    import asyncio
    asyncio.run(_collect_all_vulnerabilities())


async def _collect_all_vulnerabilities():
    async with async_session_maker() as db:
        collector = CollectorManager(db)
        for ecosystem in ["npm", "pypi", "maven"]:
            try:
                pass
            except Exception as e:
                logger.error(f"Failed to collect vulns for {ecosystem}: {e}")