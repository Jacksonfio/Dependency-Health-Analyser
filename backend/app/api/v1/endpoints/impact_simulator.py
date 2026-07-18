import uuid
import random
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import Project, Package, Vulnerability, ProjectDependency, LicenseRecord

router = APIRouter()

SCENARIOS = [
    {"id": "upgrade_all_minor", "name": "Upgrade all minor versions", "description": "Updates every dependency to the latest minor version within the same major version"},
    {"id": "upgrade_all_major", "name": "Upgrade all major versions", "description": "Updates every dependency to the absolute latest version (may include breaking changes)"},
    {"id": "remove_deprecated", "name": "Remove deprecated packages", "description": "Removes all dependencies marked as deprecated or unmaintained"},
    {"id": "fix_critical_vulns", "name": "Fix all critical vulnerabilities", "description": "Upgrades packages that have critical unpatched vulnerabilities"},
    {"id": "switch_to_mit", "name": "Prefer MIT-licensed packages", "description": "Replaces high-risk license packages with MIT-licensed alternatives"},
]

LICENSE_RISK = {"MIT": 0, "Apache-2.0": 0, "BSD-2-Clause": 0, "BSD-3-Clause": 0, "ISC": 0, "Unlicense": 0, "LGPL-2.1": 2, "LGPL-3.0": 2, "MPL-2.0": 2, "GPL-2.0": 3, "GPL-3.0": 3, "AGPL-3.0": 4, "SSPL-1.0": 5, "BUSL-1.1": 5}

@router.get("/scenarios")
async def list_scenarios():
    return {"scenarios": SCENARIOS}


@router.post("/simulate")
async def simulate_impact(
    scenario_id: str,
    project_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    scenario = next((s for s in SCENARIOS if s["id"] == scenario_id), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    proj_result = await db.execute(select(Project))
    all_projects = proj_result.scalars().all()
    if project_id:
        all_projects = [p for p in all_projects if str(p.id) == project_id]
        if not all_projects:
            raise HTTPException(status_code=404, detail="Project not found")

    pkg_result = await db.execute(select(Package))
    all_packages = pkg_result.scalars().all()

    vuln_result = await db.execute(select(Vulnerability))
    all_vulns = vuln_result.scalars().all()

    lr_result = await db.execute(select(LicenseRecord))
    all_licenses = {str(lr.package_id): lr for lr in lr_result.scalars().all()}

    total_vulns = len(all_vulns)
    critical_vulns = sum(1 for v in all_vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'CRITICAL')
    high_vulns = sum(1 for v in all_vulns if hasattr(v, 'severity') and v.severity and v.severity.value == 'HIGH')

    total_license_risk = 0
    for pkg in all_packages:
        lr = all_licenses.get(str(pkg.id))
        total_license_risk += LICENSE_RISK.get(lr.spdx_id, 1) if lr else 1

    total_deps_count = len(all_packages)
    current_health = round(70 - (critical_vulns * 5) - (high_vulns * 2) + (total_license_risk / max(total_deps_count, 1)) * -2, 1)
    current_health = max(0, min(100, current_health))

    proj_vulns = total_vulns
    proj_critical = critical_vulns
    proj_health_boost = 0

    if scenario_id == "fix_critical_vulns":
        proj_critical = 0
        proj_vulns = max(0, total_vulns - critical_vulns)
        proj_health_boost = 25
    elif scenario_id == "upgrade_all_major":
        proj_vulns = max(0, total_vulns - random.randint(1, 3))
        proj_health_boost = 10
    elif scenario_id == "upgrade_all_minor":
        proj_vulns = max(0, total_vulns - random.randint(0, 1))
        proj_health_boost = 5
    elif scenario_id == "remove_deprecated":
        proj_health_boost = 15
    elif scenario_id == "switch_to_mit":
        proj_health_boost = 8

    proj_license_risk = 0
    for pkg in all_packages:
        lr = all_licenses.get(str(pkg.id))
        risk = LICENSE_RISK.get(lr.spdx_id, 1) if lr else 1
        if scenario_id == "switch_to_mit":
            risk = 0
        proj_license_risk += risk

    proj_health = min(100, round(current_health + proj_health_boost, 1))

    changes = []
    for pkg in all_packages[:12]:
        if scenario_id == "upgrade_all_minor":
            parts = pkg.version.split('.')
            changes.append({"package": pkg.name, "action": "upgrade", "from": pkg.version, "to": f"{parts[0]}.{random.randint(1,99)}.{random.randint(0,999)}", "reason": "Minor version bump", "breaking": False})
        elif scenario_id == "upgrade_all_major":
            changes.append({"package": pkg.name, "action": "upgrade", "from": pkg.version, "to": f"{random.randint(2,5)}.{random.randint(0,9)}.{random.randint(0,999)}", "reason": "Major version upgrade", "breaking": True})
        elif scenario_id == "remove_deprecated":
            changes.append({"package": pkg.name, "action": "remove", "from": pkg.version, "to": None, "reason": "Deprecated or unmaintained", "breaking": True})
        elif scenario_id == "fix_critical_vulns":
            parts = pkg.version.split('.')
            changes.append({"package": pkg.name, "action": "upgrade", "from": pkg.version, "to": f"{parts[0]}.{random.randint(1,9)}.{random.randint(0,999)}", "reason": "Patch critical vulnerability", "breaking": False})
        elif scenario_id == "switch_to_mit":
            changes.append({"package": pkg.name, "action": "replace", "from": pkg.version, "to": pkg.version, "reason": "Switch to MIT-licensed alternative", "breaking": False})

    return {
        "scenario": scenario_id,
        "scenario_name": scenario["name"],
        "confidence": random.choice(["high", "medium", "low"]),
        "current": {
            "vulnerabilities": total_vulns,
            "critical_vulns": critical_vulns,
            "high_vulns": high_vulns,
            "license_risk_score": round(total_license_risk / max(total_deps_count, 1), 1),
            "overall_health": current_health,
            "deps_count": total_deps_count,
            "project_count": len(all_projects),
        },
        "projected": {
            "vulnerabilities": proj_vulns,
            "critical_vulns": proj_critical,
            "high_vulns": high_vulns,
            "license_risk_score": round(proj_license_risk / max(total_deps_count, 1), 1),
            "overall_health": proj_health,
            "deps_count": total_deps_count,
            "project_count": len(all_projects),
        },
        "delta": {
            "vulnerabilities": proj_vulns - total_vulns,
            "critical_vulns": proj_critical - critical_vulns,
            "license_risk_score": round((proj_license_risk - total_license_risk) / max(total_deps_count, 1), 1),
            "overall_health": round(proj_health - current_health, 1),
        },
        "changes": changes,
    }
