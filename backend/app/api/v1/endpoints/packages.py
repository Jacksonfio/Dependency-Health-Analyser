from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Package, PackageVersion, Ecosystem, Vulnerability, Severity, Project, ProjectDependency, Scan, HealthScore, HealthReport
from app.schemas import PackageResponse, PackageDetailResponse, PackageSearchResponse, VulnerabilityResponse, ScanResponse, ScanDetailResponse, HealthScoreResponse, HealthReportResponse
from app.services.scoring.engine import ScoringEngine
from app.services.collectors.manager import CollectorManager

router = APIRouter()


@router.get("/search", response_model=PackageSearchResponse)
async def search_packages(
    q: str = Query(..., min_length=1),
    ecosystem: Optional[Ecosystem] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Package).where(
        or_(
            Package.name.ilike(f"%{q}%"),
            Package.description.ilike(f"%{q}%"),
        )
    )
    if ecosystem:
        query = query.where(Package.ecosystem == ecosystem)
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.order_by(Package.dependents_count.desc().nullslast()).offset(offset).limit(limit)
    result = await db.execute(query)
    packages = result.scalars().all()
    
    return PackageSearchResponse(
        items=[PackageResponse.model_validate(p) for p in packages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{package_id}", response_model=PackageDetailResponse)
async def get_package(
    package_id: UUID,
    include_versions: bool = Query(False),
    include_vulns: bool = Query(False),
    include_health: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    query = select(Package).where(Package.id == package_id)
    
    if include_versions:
        query = query.options(selectinload(Package.versions))
    if include_vulns:
        query = query.options(selectinload(Package.vulnerabilities))
    if include_health:
        query = query.options(selectinload(Package.health_scores))
    
    result = await db.execute(query)
    package = result.scalar_one_or_none()
    
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    return PackageDetailResponse.model_validate(package)


@router.get("/{package_id}/versions", response_model=List[dict])
async def get_package_versions(
    package_id: UUID,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(PackageVersion).where(
        PackageVersion.package_id == package_id
    ).order_by(PackageVersion.published_at.desc().nullslast()).limit(limit)
    
    result = await db.execute(query)
    versions = result.scalars().all()
    
    return [
        {
            "id": str(v.id),
            "version": v.version,
            "published_at": v.published_at,
            "is_latest": v.is_latest,
            "is_deprecated": v.is_deprecated,
            "downloads": v.downloads,
        }
        for v in versions
    ]


@router.get("/{package_id}/vulnerabilities", response_model=List[VulnerabilityResponse])
async def get_package_vulnerabilities(
    package_id: UUID,
    severity: Optional[Severity] = None,
    fixed_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    query = select(Vulnerability).where(Vulnerability.package_id == package_id)
    
    if severity:
        query = query.where(Vulnerability.severity == severity)
    if fixed_only:
        query = query.where(Vulnerability.fixed_versions.isnot(None))
    
    query = query.order_by(Vulnerability.severity.desc(), Vulnerability.published_at.desc().nullslast())
    
    result = await db.execute(query)
    vulns = result.scalars().all()
    
    return [VulnerabilityResponse.model_validate(v) for v in vulns]


@router.get("/{package_id}/health", response_model=HealthScoreResponse)
async def get_package_health(
    package_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    engine = ScoringEngine(db)
    health = await engine.calculate_package_health(package_id)
    
    if not health:
        raise HTTPException(status_code=404, detail="Package not found or health not calculated")
    
    return HealthScoreResponse.model_validate(health)


@router.post("/{package_id}/refresh", response_model=dict)
async def refresh_package_data(
    package_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    package = await db.get(Package, package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    
    collector = CollectorManager(db)
    background_tasks.add_task(collector.refresh_package, package_id)
    
    return {"status": "refresh_queued", "package_id": str(package_id)}


@router.get("/ecosystem/{ecosystem}/popular", response_model=List[PackageResponse])
async def get_popular_packages(
    ecosystem: Ecosystem,
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Package).where(
        and_(
            Package.ecosystem == ecosystem,
            Package.dependents_count.isnot(None),
        )
    ).order_by(Package.dependents_count.desc()).limit(limit)
    
    result = await db.execute(query)
    packages = result.scalars().all()
    
    return [PackageResponse.model_validate(p) for p in packages]


@router.get("/{package_id}/dependents", response_model=List[dict])
async def get_package_dependents(
    package_id: UUID,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Package).join(
        ProjectDependency,
        ProjectDependency.package_id == Package.id
    ).where(
        ProjectDependency.dependent_id == package_id
    ).limit(limit)
    
    result = await db.execute(query)
    packages = result.scalars().all()
    
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "ecosystem": p.ecosystem.value,
            "dependents_count": p.dependents_count,
        }
        for p in packages
    ]


@router.get("/{package_id}/dependency-graph")
async def get_dependency_graph(
    package_id: UUID,
    depth: int = Query(2, ge=1, le=5),
    direction: str = Query("both", pattern="^(up|down|both)$"),
    db: AsyncSession = Depends(get_db),
):
    from app.services.graph.service import GraphService
    
    graph_service = GraphService(db)
    graph = await graph_service.get_dependency_graph(package_id, depth, direction)
    
    return graph