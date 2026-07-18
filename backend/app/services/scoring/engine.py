from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from app.db.models import (
    Package, PackageVersion, Vulnerability, Project, ProjectDependency,
    HealthScore, HealthReport, Scan, Alert, Severity, Ecosystem,
    ProjectDependencyVulnerability
)
from app.services.ml.risk_models import (
    FutureRiskPredictor, MaintenanceHealthModel, SecurityRiskModel, CommunityHealthModel
)
from app.services.ml.exploit_predictor import ExploitPredictor
from app.services.ml.fix_recommender import FixRecommender
from app.services.collectors.manager import CollectorManager

logger = logging.getLogger(__name__)


class ScoringEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.predictor = FutureRiskPredictor()
        self.exploit_predictor = ExploitPredictor()
        self.fix_recommender = FixRecommender(db)
        self.collector = CollectorManager(db)
    
    async def calculate_package_health(self, package_id: UUID) -> Optional[HealthScore]:
        package = await self.db.get(Package, package_id)
        if not package:
            return None
        
        package_data = await self._collect_package_features(package)
        
        prediction = self.predictor.predict_future_risk(package_data, horizon_days=90)
        
        overall_score = 100 - prediction["current_risk_score"]
        maintenance_score = prediction["component_scores"]["maintenance"]
        security_score = prediction["component_scores"]["security"]
        community_score = prediction["component_scores"]["community"]
        
        health_score = HealthScore(
            package_id=package_id,
            overall_score=overall_score,
            maintenance_score=maintenance_score,
            security_score=security_score,
            community_score=community_score,
            popularity_score=min(100, max(0, community_score * 1.2)),
            factors=prediction["factor_breakdown"],
            recommendations=[r["title"] for r in prediction["recommendations"]],
            calculated_at=datetime.utcnow(),
            valid_until=datetime.utcnow() + timedelta(days=7),
        )
        
        self.db.add(health_score)
        await self.db.flush()
        
        for rec in prediction["recommendations"]:
            if rec["priority"] in ["high", "critical"]:
                await self._create_alert(package, rec)
        
        return health_score
    
    async def _collect_package_features(self, package: Package) -> Dict[str, Any]:
        maintenance_data = await self._get_maintenance_data(package)
        security_data = await self._get_security_data(package)
        community_data = await self._get_community_data(package)
        
        return {
            "name": package.name,
            "ecosystem": package.ecosystem.value,
            "maintenance": maintenance_data,
            "security": security_data,
            "community": community_data,
        }
    
    async def _get_maintenance_data(self, package: Package) -> Dict[str, Any]:
        from app.services.collectors.github_collector import GitHubCollector
        
        github = GitHubCollector()
        repo_data = await github.get_repository_data(package.repository_url) if package.repository_url else {}
        
        last_release = None
        if package.updated_at:
            last_release = (datetime.utcnow() - package.updated_at).days
        
        releases = await self._get_release_history(package)
        release_freq = self._calculate_release_frequency(releases)
        
        return {
            "last_release_days": last_release or 365,
            "release_frequency_days": release_freq,
            "maintainer_count": len(package.maintainers) if package.maintainers else 1,
            "active_maintainer_count": repo_data.get("active_maintainers", 1),
            "commit_frequency": repo_data.get("commits_per_week", 0),
            "issue_response_time_hours": repo_data.get("avg_issue_response_hours", 720),
            "pr_merge_time_hours": repo_data.get("avg_pr_merge_hours", 168),
            "bus_factor": repo_data.get("bus_factor", 1),
            "open_issues_count": repo_data.get("open_issues", 0),
            "open_issues_trend": repo_data.get("issues_trend", 0),
            "closed_issues_count": repo_data.get("closed_issues", 0),
            "stars": repo_data.get("stars", package.dependents_count or 0),
            "forks": repo_data.get("forks", 0),
            "watchers": repo_data.get("watchers", 0),
            "contributors_count": repo_data.get("contributors", 1),
            "has_security_policy": repo_data.get("has_security_policy", False),
            "has_code_of_conduct": repo_data.get("has_code_of_conduct", False),
            "has_contributing": repo_data.get("has_contributing", False),
            "release_notes_quality": repo_data.get("release_notes_quality", 0.5),
            "dependency_update_frequency": repo_data.get("dep_update_freq", 0),
            "major_version_age_days": self._get_major_version_age(package),
            "is_archived": repo_data.get("is_archived", False),
            "is_deprecated": any(v.is_deprecated for v in package.versions) if package.versions else False,
        }
    
    async def _get_security_data(self, package: Package) -> Dict[str, Any]:
        vulns_query = select(Vulnerability).where(
            and_(
                Vulnerability.package_id == package.id,
                Vulnerability.withdrawn_at.is_(None),
            )
        ).order_by(desc(Vulnerability.published_at))
        
        result = await self.db.execute(vulns_query)
        vulns = result.scalars().all()
        
        now = datetime.utcnow()
        year_ago = now - timedelta(days=365)
        
        recent_vulns = [v for v in vulns if v.published_at and v.published_at > year_ago]
        critical = [v for v in vulns if v.severity == Severity.CRITICAL]
        high = [v for v in vulns if v.severity == Severity.HIGH]
        
        cve_velocity = len(recent_vulns)
        
        days_since_last = 365
        if vulns and vulns[0].published_at:
            days_since_last = (now - vulns[0].published_at).days
        
        cvss_scores = [v.cvss_score for v in vulns if v.cvss_score]
        
        fixed_count = sum(1 for v in vulns if v.fixed_versions)
        
        return {
            "cve_count_last_year": len(recent_vulns),
            "cve_velocity_per_year": cve_velocity,
            "critical_cve_count": len(critical),
            "high_cve_count": len(high),
            "exploit_count": 0,
            "days_since_last_cve": days_since_last,
            "avg_cvss_score": sum(cvss_scores) / len(cvss_scores) if cvss_scores else 0,
            "max_cvss_score": max(cvss_scores) if cvss_scores else 0,
            "cve_types_diversity": len(set(v.cwe_ids[0] if v.cwe_ids else "unknown" for v in vulns)),
            "affected_versions_ratio": len(vulns) / max(1, len(package.versions)) if package.versions else 0,
            "fix_availability_ratio": fixed_count / max(1, len(vulns)) if vulns else 1,
            "vendor_response_time_days": 30,
            "has_exploit_in_wild": False,
            "has_poc_exploit": False,
        }
    
    async def _get_community_data(self, package: Package) -> Dict[str, Any]:
        download_trend = await self._get_download_trend(package)
        
        return {
            "download_trend_30d": download_trend.get("30d", 0),
            "download_trend_90d": download_trend.get("90d", 0),
            "dependent_count": package.dependents_count or 0,
            "dependent_trend": 0,
            "github_stars_trend": 0,
            "fork_count_trend": 0,
            "issue_activity_trend": 0,
            "pr_activity_trend": 0,
            "migration_indicators": await self._detect_migration(package),
            "ecosystem_health_score": await self._get_ecosystem_health(package.ecosystem),
        }
    
    async def _get_release_history(self, package: Package) -> List[datetime]:
        if not package.versions:
            return []
        
        dates = [v.published_at for v in package.versions if v.published_at]
        return sorted(dates)
    
    def _calculate_release_frequency(self, releases: List[datetime]) -> float:
        if len(releases) < 2:
            return 90
        
        intervals = [(releases[i] - releases[i-1]).days for i in range(1, len(releases))]
        return sum(intervals) / len(intervals)
    
    def _get_major_version_age(self, package: Package) -> float:
        if not package.versions:
            return 365
        
        major_versions = {}
        for v in package.versions:
            try:
                from packaging import version
                ver = version.parse(v.version)
                if hasattr(ver, 'major'):
                    major = ver.major
                    if major not in major_versions or v.published_at > major_versions[major]:
                        major_versions[major] = v.published_at
            except:
                continue
        
        if not major_versions:
            return 365
        
        latest_major = max(major_versions.keys())
        latest_date = major_versions[latest_major]
        
        if latest_date:
            return (datetime.utcnow() - latest_date).days
        return 365
    
    async def _get_download_trend(self, package: Package) -> Dict[str, float]:
        return {"30d": 0, "90d": 0}
    
    async def _detect_migration(self, package: Package) -> Dict[str, float]:
        migrations = {
            "npm": {
                "moment": {"date-fns": 0.9, "dayjs": 0.8},
                "request": {"axios": 0.95, "fetch": 0.7},
                "lodash": {"es-toolkit": 0.6, "lodash-es": 0.4},
            },
            "pypi": {
                "requests": {"httpx": 0.7},
                "urllib3": {"httpx": 0.6},
            },
        }
        
        return migrations.get(package.ecosystem.value, {}).get(package.name.lower(), {})
    
    async def _get_ecosystem_health(self, ecosystem: Ecosystem) -> float:
        health_scores = {
            Ecosystem.NPM: 75,
            Ecosystem.PYPI: 80,
            Ecosystem.MAVEN: 85,
            Ecosystem.DOCKER: 70,
            Ecosystem.GO: 85,
        }
        return health_scores.get(ecosystem, 70)
    
    async def _create_alert(self, package: Package, recommendation: Dict):
        project_deps = await self.db.execute(
            select(ProjectDependency).where(
                and_(
                    ProjectDependency.ecosystem == package.ecosystem,
                    ProjectDependency.name == package.name,
                )
            ).limit(10)
        )
        deps = project_deps.scalars().all()
        
        for dep in deps:
            alert = Alert(
                project_id=dep.project_id,
                project_dependency_id=dep.id,
                alert_type="health_recommendation",
                severity=Severity.HIGH if recommendation["priority"] == "critical" else Severity.MEDIUM,
                title=recommendation["title"],
                message=recommendation["description"],
            )
            self.db.add(alert)
    
    async def generate_project_health_report(self, project_id: UUID) -> HealthReport:
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        
        deps_query = select(ProjectDependency).where(ProjectDependency.project_id == project_id)
        deps_result = await self.db.execute(deps_query)
        dependencies = deps_result.scalars().all()
        
        total_deps = len(dependencies)
        vuln_deps = 0
        outdated_deps = 0
        deprecated_deps = 0
        critical = high = medium = low = 0
        
        recommendations = []
        
        for dep in dependencies:
            if dep.package_id:
                pkg_health = await self.calculate_package_health(dep.package_id)
                if pkg_health and pkg_health.overall_score < 50:
                    vuln_deps += 1
                
                latest_version = await self._get_latest_version(dep.package_id)
                if latest_version and latest_version != dep.version:
                    outdated_deps += 1
                
                if dep.package_version and dep.package_version.is_deprecated:
                    deprecated_deps += 1
            
            vuln_query = select(Vulnerability).join(
                ProjectDependencyVulnerability,
                Vulnerability.id == ProjectDependencyVulnerability.vulnerability_id
            ).where(ProjectDependencyVulnerability.project_dependency_id == dep.id)
            
            vuln_result = await self.db.execute(vuln_query)
            vulns = vuln_result.scalars().all()
            
            for v in vulns:
                if v.severity == Severity.CRITICAL:
                    critical += 1
                elif v.severity == Severity.HIGH:
                    high += 1
                elif v.severity == Severity.MEDIUM:
                    medium += 1
                elif v.severity == Severity.LOW:
                    low += 1
        
        overall = max(0, 100 - (critical * 10 + high * 5 + medium * 2 + low * 1))
        security = max(0, 100 - (critical * 15 + high * 8 + medium * 3 + low * 1))
        maintenance = max(0, 100 - (outdated_deps * 2 + deprecated_deps * 5))
        licensing = 100
        
        report = HealthReport(
            project_id=project_id,
            overall_score=overall,
            security_score=security,
            maintenance_score=maintenance,
            licensing_score=licensing,
            total_dependencies=total_deps,
            vulnerable_dependencies=vuln_deps,
            outdated_dependencies=outdated_deps,
            deprecated_dependencies=deprecated_deps,
            critical_vulns=critical,
            high_vulns=high,
            medium_vulns=medium,
            low_vulns=low,
            recommendations=recommendations,
            details={
                "dependency_breakdown": {
                    "total": total_deps,
                    "direct": sum(1 for d in dependencies if d.is_direct),
                    "transitive": sum(1 for d in dependencies if not d.is_direct),
                },
                "vulnerability_summary": {
                    "critical": critical,
                    "high": high,
                    "medium": medium,
                    "low": low,
                },
            },
            generated_at=datetime.utcnow(),
        )
        
        self.db.add(report)
        await self.db.flush()
        
        return report
    
    async def predict_upgrade_schedule(
        self,
        project_id: UUID,
    ) -> Dict[str, Any]:
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        
        deps_query = select(ProjectDependency).where(
            and_(
                ProjectDependency.project_id == project_id,
                ProjectDependency.is_direct == True,
            )
        )
        deps_result = await self.db.execute(deps_query)
        dependencies = deps_result.scalars().all()
        
        schedule = {
            "immediate": [],
            "within_2_weeks": [],
            "within_1_month": [],
            "within_3_months": [],
            "no_action_needed": [],
        }
        
        for dep in dependencies:
            if not dep.package_id:
                continue
            
            package = await self.db.get(Package, dep.package_id)
            if not package:
                continue
            
            package_data = await self._collect_package_features(package)
            prediction = self.predictor.predict_future_risk(package_data, horizon_days=90)
            
            current_risk = prediction["current_risk_score"]
            projected_risk = prediction["projected_risk_score"]
            timeline = prediction["upgrade_timeline"]
            
            item = {
                "package": package.name,
                "current_version": dep.version,
                "ecosystem": package.ecosystem.value,
                "current_risk": current_risk,
                "projected_risk": projected_risk,
                "is_direct": dep.is_direct,
            }
            
            if timeline["immediate"]:
                schedule["immediate"].append(item)
            elif timeline["within_2_weeks"]:
                schedule["within_2_weeks"].append(item)
            elif timeline["within_1_month"]:
                schedule["within_1_month"].append(item)
            elif timeline["within_3_months"]:
                schedule["within_3_months"].append(item)
            else:
                schedule["no_action_needed"].append(item)
        
        return {
            "project_id": str(project_id),
            "generated_at": datetime.utcnow().isoformat(),
            "schedule": schedule,
            "summary": {
                "immediate_count": len(schedule["immediate"]),
                "two_weeks_count": len(schedule["within_2_weeks"]),
                "one_month_count": len(schedule["within_1_month"]),
                "three_months_count": len(schedule["within_3_months"]),
                "healthy_count": len(schedule["no_action_needed"]),
            }
        }
    
    async def _get_latest_version(self, package_id: UUID) -> Optional[str]:
        query = select(PackageVersion).where(
            and_(
                PackageVersion.package_id == package_id,
                PackageVersion.is_latest == True,
            )
        )
        result = await self.db.execute(query)
        version = result.scalar_one_or_none()
        return version.version if version else None