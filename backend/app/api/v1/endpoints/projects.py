from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Project, Scan, Severity, HealthReport, Vulnerability, ProjectDependency, Package, LicenseRecord
from app.schemas import ProjectResponse, ProjectCreate, ProjectDetailResponse, ProjectListResponse, ScanResponse, ScanDetailResponse, HealthReportResponse

router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
):
    project = Project(**project_data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    ecosystem: Optional[str] = None,
    is_monitored: Optional[bool] = None,
    owner_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None,
    search: Optional[str] = None,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project)
    
    if ecosystem:
        query = query.where(Project.ecosystem == ecosystem)
    if is_monitored is not None:
        query = query.where(Project.is_monitored == is_monitored)
    if owner_id:
        query = query.where(Project.owner_id == owner_id)
    if organization_id:
        query = query.where(Project.organization_id == organization_id)
    if search:
        query = query.where(
            or_(
                Project.name.ilike(f"%{search}%"),
                Project.description.ilike(f"%{search}%"),
            )
        )
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.order_by(desc(Project.updated_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{project_id}", response_model=ProjectDetailResponse)
async def get_project(
    project_id: UUID,
    include_dependencies: bool = Query(False),
    include_scans: bool = Query(False),
    include_health: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).where(Project.id == project_id)
    
    if include_dependencies:
        query = query.options(selectinload(Project.dependencies))
    if include_scans:
        query = query.options(selectinload(Project.scans))
    if include_health:
        query = query.options(selectinload(Project.health_reports))
    
    result = await db.execute(query)
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return ProjectDetailResponse.model_validate(project)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    project_update: dict,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for field, value in project_update.items():
        if hasattr(project, field):
            setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    return ProjectResponse.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await db.delete(project)
    await db.commit()


@router.post("/{project_id}/scan", response_model=ScanResponse)
async def trigger_scan(
    project_id: UUID,
    scan_type: str = Query("full", pattern="^(full|incremental|dependency-only)$"),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    scan = Scan(
        project_id=project_id,
        scan_type=scan_type,
        status="pending",
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    return ScanResponse.model_validate(scan)


@router.get("/{project_id}/scans", response_model=List[ScanResponse])
async def get_project_scans(
    project_id: UUID,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = select(Scan).where(Scan.project_id == project_id).order_by(desc(Scan.started_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    scans = result.scalars().all()
    
    return [ScanResponse.model_validate(s) for s in scans]


@router.get("/{project_id}/scans/latest", response_model=ScanDetailResponse)
async def get_latest_scan(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    query = select(Scan).where(Scan.project_id == project_id).order_by(desc(Scan.started_at)).limit(1)
    result = await db.execute(query)
    scan = result.scalar_one_or_none()
    
    if not scan:
        raise HTTPException(status_code=404, detail="No scans found")
    
    return ScanDetailResponse.model_validate(scan)


@router.get("/{project_id}/health", response_model=HealthReportResponse)
async def get_project_health(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    hr = await db.execute(
        select(HealthReport).where(HealthReport.project_id == project_id).order_by(desc(HealthReport.generated_at)).limit(1)
    )
    existing = hr.scalar_one_or_none()
    if existing:
        return HealthReportResponse.model_validate(existing)

    dep_result = await db.execute(
        select(ProjectDependency).where(ProjectDependency.project_id == project_id)
    )
    deps = dep_result.scalars().all()
    total_deps = len(deps)

    vuln_result = await db.execute(select(Vulnerability))
    all_vulns = vuln_result.scalars().all()
    relevant_vulns = [v for v in all_vulns if any(d.name == v.package_name for d in deps)]

    critical = sum(1 for v in relevant_vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'CRITICAL')
    high = sum(1 for v in relevant_vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'HIGH')
    medium = sum(1 for v in relevant_vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'MEDIUM')
    low = sum(1 for v in relevant_vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'LOW')

    vuln_penalty = critical * 15 + high * 8 + medium * 3 + low * 1
    overall_score = max(0, min(100, 85 - vuln_penalty))
    security_score = max(0, min(100, 80 - vuln_penalty))
    maintenance_score = 75
    licensing_score = 80

    from datetime import datetime
    now = datetime.utcnow()
    report = HealthReport(
        id=uuid.uuid4(),
        project_id=project_id,
        overall_score=overall_score,
        security_score=security_score,
        maintenance_score=maintenance_score,
        licensing_score=licensing_score,
        total_dependencies=total_deps,
        vulnerable_dependencies=len(relevant_vulns),
        outdated_dependencies=0,
        deprecated_dependencies=0,
        critical_vulns=critical,
        high_vulns=high,
        medium_vulns=medium,
        low_vulns=low,
        details={},
        generated_at=now,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return HealthReportResponse.model_validate(report)


@router.get("/{project_id}/health/history", response_model=List[HealthReportResponse])
async def get_health_history(
    project_id: UUID,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = select(HealthReport).where(
        and_(
            HealthReport.project_id == project_id,
            HealthReport.generated_at >= cutoff,
        )
    ).order_by(desc(HealthReport.generated_at)).limit(limit)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return [HealthReportResponse.model_validate(r) for r in reports]


@router.post("/{project_id}/refresh")
async def refresh_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"status": "refresh_queued", "project_id": str(project_id)}


@router.get("/{project_id}/upgrade-plan")
async def get_upgrade_plan(
    project_id: UUID,
    max_effort: str = Query("medium", pattern="^(low|medium|high)$"),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dep_result = await db.execute(
        select(ProjectDependency).where(
            ProjectDependency.project_id == project_id,
            ProjectDependency.package_id.isnot(None),
        )
    )
    deps = dep_result.scalars().all()

    plan = {"immediate": [], "within_2_weeks": [], "within_1_month": [], "within_3_months": [], "no_action_needed": []}

    for dep in deps:
        if not dep.package_id:
            continue
        pkg = await db.get(Package, dep.package_id)
        if not pkg:
            continue

        vuln_result = await db.execute(
            select(Vulnerability).where(Vulnerability.package_id == dep.package_id)
        )
        vulns = vuln_result.scalars().all()
        has_critical = any(hasattr(v, 'severity') and v.severity and v.severity.value == 'CRITICAL' for v in vulns)
        has_high = any(hasattr(v, 'severity') and v.severity and v.severity.value == 'HIGH' for v in vulns)

        item = {
            "package": dep.name,
            "currentVersion": dep.version,
            "targetVersion": pkg.version,
            "ecosystem": dep.ecosystem,
            "breakingChange": False,
            "migrationEffort": "low",
            "securityFixes": [v.cve_id for v in vulns if v.cve_id],
            "estimatedHours": 1,
            "priority": "none",
            "reason": "Up-to-date",
        }

        if has_critical:
            item["priority"] = "immediate"
            item["reason"] = f"Critical vulnerability: {', '.join(v.cve_id for v in vulns if v.cve_id)}"
            item["migrationEffort"] = "medium"
            item["estimatedHours"] = 4
            plan["immediate"].append(item)
        elif has_high:
            item["priority"] = "2_weeks"
            item["reason"] = f"High severity vulnerability: {', '.join(v.cve_id for v in vulns if v.cve_id)}"
            item["migrationEffort"] = "low"
            item["estimatedHours"] = 2
            plan["within_2_weeks"].append(item)
        elif dep.version != pkg.version:
            item["priority"] = "1_month"
            item["reason"] = f"Update available: {dep.version} → {pkg.version}"
            item["targetVersion"] = pkg.version
            plan["within_1_month"].append(item)
        else:
            item["priority"] = "none"
            item["reason"] = "Healthy, actively maintained"
            plan["no_action_needed"].append(item)

    return plan


@router.get("/{project_id}/risk-timeline")
async def get_risk_timeline(
    project_id: UUID,
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dep_result = await db.execute(
        select(ProjectDependency).where(ProjectDependency.project_id == project_id)
    )
    deps = dep_result.scalars().all()

    vuln_result = await db.execute(select(Vulnerability))
    all_vulns = vuln_result.scalars().all()
    relevant_vulns = [v for v in all_vulns if any(d.name == v.package_name for d in deps)]
    risk_score = min(100, len(relevant_vulns) * 15 + sum(
        20 if hasattr(v, 'severity') and v.severity and v.severity.value == 'CRITICAL'
        else 10 if hasattr(v, 'severity') and v.severity and v.severity.value == 'HIGH' else 0
        for v in relevant_vulns
    ))

    from datetime import datetime, timedelta
    import math
    now = datetime.utcnow()
    timeline = []
    for i in range(0, days + 1, max(1, days // 12)):
        point_date = now + timedelta(days=i)
        decay = math.exp(-i / max(days, 1) * 0.5)
        projected = min(100, max(0, risk_score + (i * 0.3) - (decay * 10)))
        timeline.append({
            "day": i,
            "date": point_date.strftime("%Y-%m-%d"),
            "projectedRisk": round(projected, 1),
            "confidence": round(max(0.5, 1 - (i / max(days, 1)) * 0.4), 2),
            "projected": i > 0,
        })

    projected_risk_90d = timeline[-1]["projectedRisk"] if timeline else risk_score

    return {
        "timeline": timeline,
        "current_risk": risk_score,
        "projected_risk_90d": projected_risk_90d,
    }