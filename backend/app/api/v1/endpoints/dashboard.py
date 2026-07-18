import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db
from app.db.models import Project, Vulnerability, HealthReport, Scan, Severity, ProjectDependency

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    proj_result = await db.execute(select(Project))
    projects = proj_result.scalars().all()
    total_projects = len(projects)

    vuln_result = await db.execute(select(Vulnerability))
    vulns = vuln_result.scalars().all()
    total_vulns = len(vulns)
    critical_vulns = sum(1 for v in vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'CRITICAL')
    high_vulns = sum(1 for v in vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'HIGH')

    dep_result = await db.execute(select(ProjectDependency))
    deps = dep_result.scalars().all()
    total_deps = len(deps)

    health_scores = []
    for proj in projects:
        hr = await db.execute(
            select(HealthReport).where(HealthReport.project_id == proj.id).order_by(HealthReport.generated_at.desc()).limit(1)
        )
        h = hr.scalar_one_or_none()
        if h:
            health_scores.append(h.overall_score)

    avg_health = round(sum(health_scores) / max(len(health_scores), 1), 1) if health_scores else None

    recent_scans = await db.execute(
        select(Scan).order_by(Scan.started_at.desc()).limit(10)
    )
    scan_count = len(recent_scans.scalars().all())

    dep_vuln_pairs = []
    for v in vulns:
        pkg_deps = await db.execute(
            select(ProjectDependency).where(
                ProjectDependency.name == v.package_name,
                ProjectDependency.ecosystem == v.ecosystem.value if hasattr(v.ecosystem, 'value') else v.ecosystem,
            )
        )
        for pd in pkg_deps.scalars().all():
            dep_vuln_pairs.append({"dep": pd.name, "vuln": v.cve_id})

    outdated_count = sum(1 for d in deps if d.is_direct) if deps else 0

    return {
        "total_projects": total_projects,
        "total_vulnerabilities": total_vulns,
        "critical_vulnerabilities": critical_vulns,
        "high_vulnerabilities": high_vulns,
        "total_dependencies": total_deps,
        "average_health_score": avg_health,
        "scans_performed": scan_count,
        "outdated_dependencies": outdated_count,
        "affected_dependencies": len(dep_vuln_pairs),
    }


@router.get("/alerts")
async def get_dashboard_alerts(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    alerts = []

    vuln_result = await db.execute(
        select(Vulnerability).order_by(Vulnerability.published_at.desc().nullslast()).limit(5)
    )
    for v in vuln_result.scalars().all():
        severity = v.severity.value if hasattr(v.severity, 'value') else str(v.severity)
        alerts.append({
            "id": str(v.id),
            "type": "vulnerability",
            "severity": severity,
            "title": f"New {severity} vulnerability: {v.cve_id or 'unknown'}",
            "message": f"{v.package_name} — {v.summary or 'No details'}",
            "timestamp": (v.published_at or datetime.utcnow()).isoformat(),
            "read": False,
        })

    scan_result = await db.execute(
        select(Scan).order_by(Scan.started_at.desc()).limit(5)
    )
    for s in scan_result.scalars().all():
        proj = await db.get(Project, s.project_id) if s.project_id else None
        alerts.append({
            "id": str(s.id) + "_scan",
            "type": "scan",
            "severity": "info",
            "title": f"Scan {'completed' if s.status == 'completed' else s.status}",
            "message": f"{proj.name if proj else 'Unknown'} — {s.total_dependencies or 0} deps, {s.vulnerable_dependencies or 0} vulns" if proj else f"Scan {s.status}",
            "timestamp": (s.completed_at or s.started_at or datetime.utcnow()).isoformat(),
            "read": False,
        })

    alerts.sort(key=lambda a: a["timestamp"], reverse=True)
    return {"alerts": alerts[:limit], "unread_count": len(alerts)}
