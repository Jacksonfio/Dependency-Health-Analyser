import uuid
import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.db.models import Project, Ecosystem, Package, PackageVersion, Vulnerability, Severity, HealthReport, Scan
from app.schemas import ProjectResponse, ProjectListResponse

router = APIRouter()

DEMO_PROJECTS = [
    {"name": "frontend-app", "ecosystem": "npm", "package_manager": "npm"},
    {"name": "backend-api", "ecosystem": "pypi", "package_manager": "pip"},
    {"name": "mobile-app", "ecosystem": "npm", "package_manager": "npm"},
    {"name": "data-pipeline", "ecosystem": "maven", "package_manager": "maven"},
]

DEMO_PACKAGES = [
    {"name": "openssl", "ecosystem": "docker", "version": "1.1.1w"},
    {"name": "axios", "ecosystem": "npm", "version": "1.6.0"},
    {"name": "lodash", "ecosystem": "npm", "version": "4.17.21"},
    {"name": "express", "ecosystem": "npm", "version": "4.18.2"},
    {"name": "uuid", "ecosystem": "npm", "version": "9.0.1"},
    {"name": "requests", "ecosystem": "pypi", "version": "2.31.0"},
    {"name": "fastapi", "ecosystem": "pypi", "version": "0.109.0"},
    {"name": "log4j", "ecosystem": "maven", "version": "2.20.0"},
]

DEMO_VULNS = [
    {"cve_id": "CVE-2024-XXXX", "package_name": "openssl", "ecosystem": "docker", "severity": "CRITICAL", "cvss_score": 9.8, "affected_versions": ["1.1.1w"], "summary": "Buffer overflow in TLS handshake"},
    {"cve_id": "CVE-2024-ZZZZ", "package_name": "axios", "ecosystem": "npm", "severity": "HIGH", "cvss_score": 7.5, "affected_versions": ["1.6.0"], "fixed_versions": ["1.7.2"], "summary": "SSRF vulnerability in axios"},
    {"cve_id": "CVE-2024-YYYY", "package_name": "openssl", "ecosystem": "docker", "severity": "HIGH", "cvss_score": 7.2, "affected_versions": ["1.1.1w"], "summary": "Denial of service via certificate"},
    {"cve_id": "GHSA-xxxx", "package_name": "lodash", "ecosystem": "npm", "severity": "MEDIUM", "cvss_score": 5.6, "affected_versions": ["4.17.21"], "fixed_versions": ["4.17.22"], "summary": "Prototype pollution in lodash"},
    {"cve_id": "CVE-2024-WWWW", "package_name": "express", "ecosystem": "npm", "severity": "MEDIUM", "cvss_score": 5.1, "affected_versions": ["4.18.2"], "summary": "Path traversal in express"},
]


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(func.count()).select_from(Project))
    if existing and existing > 0:
        raise HTTPException(status_code=400, detail="Database already has data. Delete existing data first.")

    created_projects = []
    for p_data in DEMO_PROJECTS:
        project = Project(
            id=uuid.uuid4(),
            name=p_data["name"],
            ecosystem=p_data["ecosystem"],
            package_manager=p_data["package_manager"],
            is_monitored=True,
            repository_url=f"https://github.com/org/{p_data['name']}",
        )
        db.add(project)
        await db.flush()
        created_projects.append(project)

        scan = Scan(
            project_id=project.id,
            status="completed",
            scan_type="full",
            total_dependencies=random.randint(40, 250),
            vulnerable_dependencies=random.randint(0, 5),
            critical_count=random.randint(0, 1),
            high_count=random.randint(0, 3),
            medium_count=random.randint(0, 5),
            low_count=random.randint(0, 3),
            started_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
            completed_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
        )
        db.add(scan)

        health = HealthReport(
            project_id=project.id,
            overall_score=random.uniform(40, 95),
            security_score=random.uniform(40, 95),
            maintenance_score=random.uniform(50, 90),
            licensing_score=random.uniform(60, 100),
            total_dependencies=random.randint(40, 250),
            vulnerable_dependencies=random.randint(0, 5),
            outdated_dependencies=random.randint(0, 20),
            deprecated_dependencies=random.randint(0, 10),
            critical_vulns=random.randint(0, 1),
            high_vulns=random.randint(0, 3),
            medium_vulns=random.randint(0, 5),
            low_vulns=random.randint(0, 3),
            details={},
            generated_at=datetime.utcnow(),
        )
        db.add(health)

    created_packages = []
    for pkg_data in DEMO_PACKAGES:
        pkg = Package(
            id=uuid.uuid4(),
            name=pkg_data["name"],
            ecosystem=pkg_data["ecosystem"],
            version=pkg_data["version"],
        )
        db.add(pkg)
        await db.flush()
        created_packages.append(pkg)

        pv = PackageVersion(
            package_id=pkg.id,
            version=pkg_data["version"],
            is_latest=True,
            published_at=datetime.utcnow() - timedelta(days=random.randint(30, 365)),
        )
        db.add(pv)

    for v_data in DEMO_VULNS:
        matched_pkg = next((p for p in created_packages if p.name == v_data["package_name"] and p.ecosystem == v_data["ecosystem"]), None)
        vuln = Vulnerability(
            id=uuid.uuid4(),
            cve_id=v_data["cve_id"],
            package_name=v_data["package_name"],
            ecosystem=v_data["ecosystem"],
            severity=v_data["severity"],
            cvss_score=v_data["cvss_score"],
            affected_versions=v_data["affected_versions"],
            fixed_versions=v_data.get("fixed_versions"),
            summary=v_data.get("summary"),
            package_id=matched_pkg.id if matched_pkg else None,
            published_at=datetime.utcnow() - timedelta(days=random.randint(1, 90)),
        )
        db.add(vuln)

    await db.commit()

    return {
        "status": "ok",
        "projects_created": len(created_projects),
        "packages_created": len(created_packages),
        "vulnerabilities_created": len(DEMO_VULNS),
    }
