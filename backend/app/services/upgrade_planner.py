from typing import Dict, List, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.db.models import Project, ProjectDependency, Package, PackageVersion, Vulnerability, Severity
from app.services.ml.risk_models import FutureRiskPredictor


class UpgradePlanner:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.predictor = FutureRiskPredictor()
    
    async def generate_plan(self, project_id: UUID, max_effort: str = "medium") -> Dict[str, Any]:
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        
        deps_query = select(ProjectDependency).where(
            and_(
                ProjectDependency.project_id == project_id,
                ProjectDependency.is_direct == True,
            )
        ).options(selectinload(ProjectDependency.package))
        
        result = await self.db.execute(deps_query)
        dependencies = result.scalars().all()
        
        plan = {
            "immediate": [],
            "within_2_weeks": [],
            "within_1_month": [],
            "within_3_months": [],
            "no_action_needed": [],
        }
        
        effort_order = {"low": 0, "medium": 1, "high": 2, "very_high": 3}
        max_effort_level = effort_order.get(max_effort, 1)
        
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
                plan["immediate"].append(item)
            elif timeline["within_2_weeks"]:
                plan["within_2_weeks"].append(item)
            elif timeline["within_1_month"]:
                plan["within_1_month"].append(item)
            elif timeline["within_3_months"]:
                plan["within_3_months"].append(item)
            else:
                plan["no_action_needed"].append(item)
        
        return {
            "project_id": str(project_id),
            "generated_at": datetime.utcnow().isoformat(),
            "schedule": plan,
            "summary": {
                "immediate_count": len(plan["immediate"]),
                "two_weeks_count": len(plan["within_2_weeks"]),
                "one_month_count": len(plan["within_1_month"]),
                "three_months_count": len(plan["within_3_months"]),
                "healthy_count": len(plan["no_action_needed"]),
            }
        }
    
    async def _collect_package_features(self, package: Package) -> Dict[str, Any]:
        from app.services.collectors.github_collector import GitHubCollector
        
        github = GitHubCollector()
        repo_data = await github.get_repository_data(package.repository_url) if package.repository_url else {}
        
        maintenance_data = {
            "last_release_days": 365,
            "release_frequency_days": 90,
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
            "major_version_age_days": 365,
            "is_archived": repo_data.get("is_archived", False),
            "is_deprecated": any(v.is_deprecated for v in package.versions) if package.versions else False,
        }
        
        from app.db.models import Vulnerability
        vulns_query = select(Vulnerability).where(
            and_(
                Vulnerability.package_id == package.id,
                Vulnerability.withdrawn_at.is_(None),
            )
        ).order_by(Vulnerability.published_at.desc().nullslast())
        
        vulns_result = await self.db.execute(vulns_query)
        vulns = vulns_result.scalars().all()
        
        from datetime import timedelta
        now = datetime.utcnow()
        year_ago = now - timedelta(days=365)
        
        recent_vulns = [v for v in vulns if v.published_at and v.published_at > year_ago]
        critical = [v for v in vulns if v.severity == Severity.CRITICAL]
        high = [v for v in vulns if v.severity == Severity.HIGH]
        
        cvss_scores = [v.cvss_score for v in vulns if v.cvss_score]
        
        days_since_last = 365
        if vulns and vulns[0].published_at:
            days_since_last = (now - vulns[0].published_at).days
        
        fixed_count = sum(1 for v in vulns if v.fixed_versions)
        
        security_data = {
            "cve_count_last_year": len(recent_vulns),
            "cve_velocity_per_year": len(recent_vulns),
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
        
        download_trend = await self._get_download_trend(package)
        migration_indicators = await self._detect_migration(package)
        
        community_data = {
            "download_trend_30d": download_trend.get("30d", 0),
            "download_trend_90d": download_trend.get("90d", 0),
            "dependent_count": package.dependents_count or 0,
            "dependent_trend": 0,
            "github_stars_trend": 0,
            "fork_count_trend": 0,
            "issue_activity_trend": 0,
            "pr_activity_trend": 0,
            "migration_indicators": migration_indicators,
            "ecosystem_health_score": await self._get_ecosystem_health(package.ecosystem),
        }
        
        return {
            "name": package.name,
            "ecosystem": package.ecosystem.value,
            "maintenance": maintenance_data,
            "security": security_data,
            "community": community_data,
        }
    
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
    
    async def _get_ecosystem_health(self, ecosystem) -> float:
        health_scores = {
            "npm": 75,
            "pypi": 80,
            "maven": 85,
            "docker": 70,
            "go": 85,
        }
        return health_scores.get(ecosystem.value, 70)