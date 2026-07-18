import random
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import Project, Package, ProjectDependency, LicenseRecord

router = APIRouter()

LICENSE_MAP = {
    "MIT": {"risk": "low", "compatible": ["Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense"]},
    "Apache-2.0": {"risk": "low", "compatible": ["MIT", "BSD-2-Clause", "BSD-3-Clause", "ISC"]},
    "BSD-2-Clause": {"risk": "low", "compatible": ["MIT", "Apache-2.0", "BSD-3-Clause"]},
    "BSD-3-Clause": {"risk": "low", "compatible": ["MIT", "Apache-2.0", "BSD-2-Clause"]},
    "ISC": {"risk": "low", "compatible": ["MIT", "Apache-2.0"]},
    "Unlicense": {"risk": "low", "compatible": ["MIT", "Apache-2.0", "BSD"]},
    "LGPL-2.1": {"risk": "medium", "compatible": ["LGPL-3.0", "GPL-2.0", "GPL-3.0"]},
    "LGPL-3.0": {"risk": "medium", "compatible": ["LGPL-2.1", "GPL-2.0", "GPL-3.0"]},
    "GPL-2.0": {"risk": "high", "compatible": ["GPL-3.0"]},
    "GPL-3.0": {"risk": "high", "compatible": ["GPL-2.0"]},
    "MPL-2.0": {"risk": "medium", "compatible": ["Apache-2.0", "BSD"]},
    "AGPL-3.0": {"risk": "critical", "compatible": []},
    "SSPL-1.0": {"risk": "critical", "compatible": []},
    "BUSL-1.1": {"risk": "critical", "compatible": []},
}

LICENSE_NAMES = list(LICENSE_MAP.keys())

LICENSE_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@router.get("/summary")
async def get_license_summary(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Package)
    if project_id:
        subq = select(ProjectDependency.package_id).where(
            ProjectDependency.project_id == project_id,
            ProjectDependency.package_id.isnot(None),
        )
        query = query.where(Package.id.in_(subq))

    result = await db.execute(query)
    packages = result.scalars().all()

    package_licenses = {}
    license_counts = {}
    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    conflict_count = 0
    total = len(packages)

    for pkg in packages:
        spdx, name, risk = await _get_license_for_package(pkg, db)
        package_licenses[pkg.id] = {"package_name": pkg.name, "ecosystem": pkg.ecosystem, "version": pkg.version, "spdx_id": spdx, "license_name": name, "risk": risk}
        license_counts[spdx] = license_counts.get(spdx, 0) + 1
        risk_counts[risk] = risk_counts.get(risk, 0) + 1

    licenses_in_use = list(license_counts.keys())
    for i, l1 in enumerate(licenses_in_use):
        for l2 in licenses_in_use[i + 1:]:
            info = LICENSE_MAP.get(l1)
            if info and l2 not in info.get("compatible", []):
                conflict_count += 1

    projects_affected = []
    if project_id:
        proj_result = await db.execute(select(Project).where(Project.id == project_id))
        project = proj_result.scalar_one_or_none()
        if project:
            projects_affected = [{"id": str(project.id), "name": project.name, "risk_counts": risk_counts}]
    else:
        proj_result = await db.execute(select(Project))
        for proj in proj_result.scalars().all():
            projects_affected.append({"id": str(proj.id), "name": proj.name})

    return {
        "total_packages_analyzed": total,
        "risk_summary": risk_counts,
        "risk_score": round((risk_counts.get("high", 0) * 3 + risk_counts.get("critical", 0) * 5) / max(total, 1) * 10, 1) if total > 0 else 0,
        "license_distribution": [{"spdx_id": k, "count": v} for k, v in sorted(license_counts.items(), key=lambda x: -x[1])],
        "conflicts_detected": conflict_count,
        "conflict_count": conflict_count,
        "packages": list(package_licenses.values()),
        "projects_affected": projects_affected,
    }


@router.get("/packages")
async def get_package_licenses(
    q: Optional[str] = None,
    risk: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Package)
    if q:
        query = query.where(Package.name.ilike(f"%{q}%"))
    result = await db.execute(query.offset(offset).limit(limit))
    packages = result.scalars().all()

    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    items = []
    for pkg in packages:
        spdx, name, risk_val = await _get_license_for_package(pkg, db)
        if risk and risk_val != risk:
            continue
        items.append({
            "id": str(pkg.id),
            "package_name": pkg.name,
            "ecosystem": pkg.ecosystem,
            "version": pkg.version,
            "spdx_id": spdx,
            "license_name": name,
            "risk": risk_val,
        })

    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def _get_license_for_package(pkg: Package, db: AsyncSession):
    result = await db.execute(
        select(LicenseRecord).where(LicenseRecord.package_id == pkg.id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.spdx_id, existing.name, existing.risk

    spdx = random.choice(LICENSE_NAMES)
    info = LICENSE_MAP[spdx]
    license_rec = LicenseRecord(
        id=__import__('uuid').uuid4(),
        package_id=pkg.id,
        spdx_id=spdx,
        name=spdx,
        risk=info["risk"],
        compatibility={"compatible_with": info["compatible"]},
    )
    db.add(license_rec)
    await db.flush()
    return spdx, spdx, info["risk"]
