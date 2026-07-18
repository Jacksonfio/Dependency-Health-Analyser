import uuid
import asyncio
import logging
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Project, Package, PackageVersion, Vulnerability, Severity, Scan
from app.services.collectors.registry_collectors import NPMCollector, PyPICollector
from app.services.collectors.osv_collector import OSVCollector

logger = logging.getLogger(__name__)
router = APIRouter()

DEPS_MAP = {
    "npm": ["lodash", "express", "axios"],
    "pypi": ["requests", "fastapi", "flask"],
    "maven": ["log4j:log4j", "com.google.guava:guava", "com.fasterxml.jackson.core:jackson-databind"],
    "docker": ["alpine", "python", "node"],
}


@router.post("/scan-project")
async def live_scan_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scan = Scan(project_id=project.id, scan_type="full", status="in_progress", started_at=datetime.utcnow())
    db.add(scan)
    await db.flush()

    try:
        eco = project.ecosystem.value if hasattr(project.ecosystem, 'value') else project.ecosystem
        deps_to_scan = DEPS_MAP.get(eco, DEPS_MAP["npm"])

        if eco == "npm":
            collector = NPMCollector()
        elif eco == "pypi":
            collector = PyPICollector()
        else:
            scan.status = "failed"
            scan.error_message = f"Unsupported ecosystem: {eco}"
            await db.commit()
            return {"status": "failed", "error": scan.error_message}

        osv = OSVCollector()
        fetched = []
        vuln_count = critical = high = medium = low = 0

        async def scan_dep(name):
            nonlocal vuln_count, critical, high, medium, low
            try:
                data = await collector.fetch_package(name)
                if not data:
                    return None
                existing = await db.execute(select(Package).where(Package.name == name, Package.ecosystem == project.ecosystem))
                pkg = existing.scalar_one_or_none()
                if not pkg:
                    pkg = Package(id=uuid.uuid4(), name=name, ecosystem=project.ecosystem, version=data.get("versions", [{}])[0].get("version", "0.0.0"))
                    db.add(pkg)
                    await db.flush()
                fetched.append(pkg)
                osv_vulns = await osv.query_vulnerabilities(eco.upper(), name)
                for vd in osv_vulns:
                    ev = await db.execute(select(Vulnerability).where(Vulnerability.cve_id == vd.get("cve_id")))
                    if ev.scalar_one_or_none():
                        continue
                    sev = (vd.get("severity") or "MEDIUM").upper()
                    se = getattr(Severity, sev, Severity.MEDIUM)
                    db.add(Vulnerability(id=uuid.uuid4(), cve_id=vd.get("cve_id"), ecosystem=project.ecosystem, package_name=name, package_id=pkg.id, severity=se, cvss_score=vd.get("cvss_score"), summary=vd.get("summary"), affected_versions=vd.get("affected_versions", []), fixed_versions=vd.get("fixed_versions"), published_at=datetime.utcnow()))
                    vuln_count += 1
                    if sev == "CRITICAL": critical += 1
                    elif sev == "HIGH": high += 1
                    elif sev == "MEDIUM": medium += 1
                    else: low += 1
                return pkg
            except Exception as e:
                logger.warning(f"Error scanning {name}: {e}")
                return None

        await asyncio.gather(*[scan_dep(d) for d in deps_to_scan])

        if hasattr(collector, 'close'):
            await collector.close()

        scan.status = "completed"
        scan.total_dependencies = len(fetched)
        scan.vulnerable_dependencies = vuln_count
        scan.critical_count = critical
        scan.high_count = high
        scan.medium_count = medium
        scan.low_count = low
        scan.completed_at = datetime.utcnow()
        project.last_scanned_at = datetime.utcnow()
        await db.commit()

        return {"status": "completed", "project": project.name, "packages_fetched": len(fetched), "vulnerabilities_found": vuln_count, "critical": critical, "high": high, "medium": medium, "low": low}

    except Exception as e:
        scan.status = "failed"
        scan.error_message = str(e)
        await db.commit()
        return {"status": "failed", "error": str(e)}


@router.post("/scan-all")
async def live_scan_all_projects(db: AsyncSession = Depends(get_db)):
    proj_result = await db.execute(select(Project))
    projects = proj_result.scalars().all()
    results = []
    for proj in projects:
        try:
            r = await live_scan_project(proj.id, db)
            results.append({"project": proj.name, "status": r.get("status"), "vulns": r.get("vulnerabilities_found", 0)})
        except Exception as e:
            results.append({"project": proj.name, "status": "failed", "error": str(e)})
    return {"results": results, "total_vulns": sum(r.get("vulns", 0) for r in results)}
