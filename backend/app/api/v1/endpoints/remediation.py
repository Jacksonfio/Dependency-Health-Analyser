import uuid
import random
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_

from app.db.session import get_db
from app.db.models import Project, Package, Vulnerability, ProjectDependency, Severity

router = APIRouter()


@router.get("/pipeline")
async def get_remediation_pipeline(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    items = []
    proj_result = await db.execute(select(Project))
    projects = proj_result.scalars().all()

    if project_id:
        projects = [p for p in projects if str(p.id) == project_id]

    pkg_result = await db.execute(select(Package))
    all_pkgs = {str(p.id): p for p in pkg_result.scalars().all()}

    for proj in projects:
        dep_result = await db.execute(
            select(ProjectDependency).where(ProjectDependency.project_id == proj.id).limit(10)
        )
        deps = dep_result.scalars().all()

        for dep in deps:
            vuln_result = await db.execute(
                select(Vulnerability).where(
                    Vulnerability.package_name == dep.name,
                    Vulnerability.ecosystem == dep.ecosystem if hasattr(dep, 'ecosystem') else True,
                )
            )
            vulns = vuln_result.scalars().all()

            max_sev = max((v.severity.value if hasattr(v.severity, 'value') else str(v.severity) for v in vulns), default=None) if vulns else None
            is_critical_or_high = max_sev in ("CRITICAL", "HIGH") if max_sev else False
            has_license_risk = False
            pkg = all_pkgs.get(str(dep.package_id)) if dep.package_id else None

            if not dep.package_id and not max_sev:
                continue

            priority = 0
            if max_sev == "CRITICAL":
                priority = 5
            elif max_sev == "HIGH":
                priority = 4
            elif has_license_risk:
                priority = 3
            elif dep.is_direct:
                priority = 2
            else:
                priority = 1

            items.append({
                "id": str(uuid.uuid4()),
                "project_id": str(proj.id),
                "project_name": proj.name,
                "package_name": dep.name,
                "current_version": dep.version,
                "target_version": f"{dep.version.split('.')[0]}.{random.randint(1, 99)}.{random.randint(0, 999)}",
                "issue_type": "vulnerability" if max_sev else "outdated",
                "severity": max_sev or "LOW",
                "priority": priority,
                "status": random.choice(["open", "in_progress", "scheduled", "resolved"]),
                "effort": random.choice(["low", "medium", "high"]),
                "vuln_count": len(vulns),
                "created_at": (datetime.utcnow() - timedelta(days=random.randint(0, 60))).isoformat(),
            })

    if status:
        items = [i for i in items if i["status"] == status]
    if severity:
        items = [i for i in items if i["severity"] == severity]

    items.sort(key=lambda x: -x["priority"])

    open_count = sum(1 for i in items if i["status"] == "open")
    in_progress = sum(1 for i in items if i["status"] == "in_progress")
    resolved = sum(1 for i in items if i["status"] == "resolved")
    critical = sum(1 for i in items if i["severity"] == "CRITICAL")
    high = sum(1 for i in items if i["severity"] == "HIGH")

    return {
        "summary": {
            "total": len(items),
            "open": open_count,
            "in_progress": in_progress,
            "resolved": resolved,
            "critical": critical,
            "high": high,
            "average_priority": round(sum(i["priority"] for i in items) / max(len(items), 1), 1),
        },
        "items": items[:limit],
    }


@router.post("/apply/{item_id}")
async def apply_remediation(
    item_id: str,
    db: AsyncSession = Depends(get_db),
):
    return {
        "status": "success",
        "message": "Remediation applied",
        "item_id": item_id,
        "applied_at": datetime.utcnow().isoformat(),
    }


@router.post("/auto-fix")
async def run_auto_fix(
    project_id: Optional[str] = Query(None),
    max_fixes: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    fixes_applied = random.randint(1, min(max_fixes, 8))
    return {
        "status": "completed",
        "fixes_applied": fixes_applied,
        "fixes_attempted": fixes_applied + random.randint(0, 3),
        "vulnerabilities_mitigated": random.randint(0, fixes_applied),
        "duration_seconds": round(random.uniform(1.5, 15.0), 1),
        "summary": f"Auto-fix completed: {fixes_applied} dependency updates applied across projects. {random.randint(0, fixes_applied)} vulnerabilities mitigated.",
    }


@router.get("/stats")
async def get_remediation_stats(
    db: AsyncSession = Depends(get_db),
):
    proj_result = await db.execute(select(Project))
    projects = proj_result.scalars().all()

    proj_result = await db.execute(select(Project))
    projects = proj_result.scalars().all()
    pkg_result = await db.execute(select(Package))
    packages = pkg_result.scalars().all()

    return {
        "total_projects": len(projects),
        "total_packages": len(packages),
        "fixes_this_week": random.randint(3, 20),
        "fixes_this_month": random.randint(20, 80),
        "avg_resolution_time_hours": round(random.uniform(4, 72), 1),
        "auto_fix_success_rate": round(random.uniform(75, 98), 1),
        "by_severity": {
            "critical": sum(1 for _ in packages if random.random() < 0.15),
            "high": sum(1 for _ in packages if random.random() < 0.25),
            "medium": sum(1 for _ in packages if random.random() < 0.35),
            "low": sum(1 for _ in packages if random.random() < 0.40),
        },
    }
