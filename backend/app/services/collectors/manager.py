from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime, timedelta
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import (
    Package, PackageVersion, Vulnerability, Project, ProjectDependency,
    Ecosystem, Severity
)
from app.services.collectors.github_collector import GitHubCollector
from app.services.collectors.osv_collector import OSVCollector
from app.services.collectors.registry_collectors import NPMCollector, PyPICollector, MavenCollector, DockerCollector

logger = logging.getLogger(__name__)


class CollectorManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.github = GitHubCollector()
        self.osv = OSVCollector()
        self.collectors = {
            Ecosystem.NPM: NPMCollector(),
            Ecosystem.MAVEN: MavenCollector(),
            Ecosystem.PYPI: PyPICollector(),
            Ecosystem.DOCKER: DockerCollector(),
        }
    
    async def collect_package(self, ecosystem: Ecosystem, name: str) -> Optional[Package]:
        collector = self.collectors.get(ecosystem)
        if not collector:
            logger.warning(f"No collector for ecosystem: {ecosystem}")
            return None
        
        try:
            package_data = await collector.fetch_package(name)
            if not package_data:
                return None
            
            package = await self._upsert_package(package_data)
            
            await self._collect_vulnerabilities(package)
            
            if package.repository_url:
                await self._collect_github_data(package)
            
            return package
        except Exception as e:
            logger.error(f"Error collecting package {ecosystem.value}/{name}: {e}")
            return None
    
    async def _upsert_package(self, data: Dict[str, Any]) -> Package:
        ecosystem = Ecosystem(data["ecosystem"])
        name = data["name"]
        
        query = select(Package).where(
            and_(Package.ecosystem == ecosystem, Package.name == name)
        )
        result = await self.db.execute(query)
        package = result.scalar_one_or_none()
        
        if not package:
            package = Package(ecosystem=ecosystem, name=name)
            self.db.add(package)
        
        package.description = data.get("description")
        package.homepage = data.get("homepage")
        package.repository_url = data.get("repository_url")
        package.license = data.get("license")
        package.keywords = data.get("keywords")
        package.downloads_last_month = data.get("downloads_last_month")
        package.dependents_count = data.get("dependents_count")
        package.maintainers = data.get("maintainers")
        package.updated_at = datetime.utcnow()
        
        await self._upsert_versions(package, data.get("versions", []))
        
        await self.db.flush()
        return package
    
    async def _upsert_versions(self, package: Package, versions_data: List[Dict]):
        for v_data in versions_data:
            query = select(PackageVersion).where(
                and_(
                    PackageVersion.package_id == package.id,
                    PackageVersion.version == v_data["version"]
                )
            )
            result = await self.db.execute(query)
            version = result.scalar_one_or_none()
            
            if not version:
                version = PackageVersion(package_id=package.id, version=v_data["version"])
                self.db.add(version)
            
            version.published_at = v_data.get("published_at")
            version.is_latest = v_data.get("is_latest", False)
            version.is_deprecated = v_data.get("is_deprecated", False)
            version.deprecation_reason = v_data.get("deprecation_reason")
            version.downloads = v_data.get("downloads")
            version.size_bytes = v_data.get("size_bytes")
        
        if versions_data:
            latest = max(versions_data, key=lambda v: v.get("published_at") or datetime.min)
            query = select(PackageVersion).where(
                and_(
                    PackageVersion.package_id == package.id,
                    PackageVersion.version == latest["version"]
                )
            )
            result = await self.db.execute(query)
            latest_version = result.scalar_one_or_none()
            if latest_version:
                latest_version.is_latest = True
    
    async def _collect_vulnerabilities(self, package: Package):
        vulns = await self.osv.query_vulnerabilities(package.ecosystem.value, package.name)
        
        for v_data in vulns:
            await self._upsert_vulnerability(package, v_data)
    
    async def _upsert_vulnerability(self, package: Package, v_data: Dict[str, Any]) -> Optional[Vulnerability]:
        cve_id = v_data.get("cve_id")
        osv_id = v_data.get("osv_id")
        ghsa_id = v_data.get("ghsa_id")
        
        query = select(Vulnerability).where(
            and_(
                Vulnerability.ecosystem == package.ecosystem,
                Vulnerability.package_name == package.name,
            )
        )
        
        if cve_id:
            query = query.where(Vulnerability.cve_id == cve_id)
        elif osv_id:
            query = query.where(Vulnerability.osv_id == osv_id)
        elif ghsa_id:
            query = query.where(Vulnerability.ghsa_id == ghsa_id)
        else:
            return None
        
        result = await self.db.execute(query)
        vuln = result.scalar_one_or_none()
        
        if not vuln:
            vuln = Vulnerability(
                ecosystem=package.ecosystem,
                package_name=package.name,
                package_id=package.id,
            )
            self.db.add(vuln)
        
        vuln.cve_id = cve_id
        vuln.osv_id = osv_id
        vuln.ghsa_id = ghsa_id
        vuln.affected_versions = v_data.get("affected_versions", [])
        vuln.fixed_versions = v_data.get("fixed_versions")
        vuln.summary = v_data.get("summary")
        vuln.details = v_data.get("details")
        vuln.severity = Severity(v_data.get("severity", "MEDIUM"))
        vuln.cvss_score = v_data.get("cvss_score")
        vuln.cvss_vector = v_data.get("cvss_vector")
        vuln.cwe_ids = v_data.get("cwe_ids")
        vuln.references = v_data.get("references")
        vuln.published_at = v_data.get("published_at")
        vuln.modified_at = v_data.get("modified_at")
        vuln.updated_at = datetime.utcnow()
        
        return vuln
    
    async def _collect_github_data(self, package: Package):
        if not package.repository_url:
            return
        
        try:
            repo_data = await self.github.get_repository_data(package.repository_url)
            
            package.maintainers = repo_data.get("maintainers")
            package.dependents_count = repo_data.get("dependents_count", package.dependents_count)
            
            if repo_data.get("latest_release"):
                latest = repo_data["latest_release"]
                version_query = select(PackageVersion).where(
                    and_(
                        PackageVersion.package_id == package.id,
                        PackageVersion.version == latest["version"]
                    )
                )
                result = await self.db.execute(version_query)
                version = result.scalar_one_or_none()
                
                if not version:
                    version = PackageVersion(
                        package_id=package.id,
                        version=latest["version"],
                        published_at=latest.get("published_at"),
                        is_latest=True,
                    )
                    self.db.add(version)
                else:
                    version.is_latest = True
                    version.published_at = latest.get("published_at")
        
        except Exception as e:
            logger.warning(f"Failed to collect GitHub data for {package.name}: {e}")
    
    async def refresh_package(self, package_id: UUID):
        package = await self.db.get(Package, package_id)
        if not package:
            return
        
        await self.collect_package(package.ecosystem, package.name)
        await self.db.commit()
    
    async def refresh_project(self, project_id: UUID):
        project = await self.db.get(Project, project_id)
        if not project:
            return
        
        for dep in project.dependencies:
            if dep.package_id:
                await self.refresh_package(dep.package_id)
        
        project.last_scanned_at = datetime.utcnow()
        await self.db.commit()
    
    async def collect_ecosystem_vulnerabilities(self, ecosystem: Ecosystem, days: int = 7):
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        vulns = await self.osv.query_recent_vulnerabilities(ecosystem.value, days)
        
        for v_data in vulns:
            package_name = v_data.get("package_name")
            if not package_name:
                continue
            
            pkg_query = select(Package).where(
                and_(Package.ecosystem == ecosystem, Package.name == package_name)
            )
            pkg_result = await self.db.execute(pkg_query)
            package = pkg_result.scalar_one_or_none()
            
            if not package:
                package = await self.collect_package(ecosystem, package_name)
            
            if package:
                await self._upsert_vulnerability(package, v_data)
        
        await self.db.commit()
    
    async def get_ecosystem_stats(self, ecosystem: Ecosystem) -> Dict[str, Any]:
        total_packages = await self.db.scalar(
            select(func.count(Package.id)).where(Package.ecosystem == ecosystem)
        )
        
        total_vulns = await self.db.scalar(
            select(func.count(Vulnerability.id)).where(Vulnerability.ecosystem == ecosystem)
        )
        
        return {
            "ecosystem": ecosystem.value,
            "total_packages": total_packages,
            "total_vulnerabilities": total_vulns,
        }