from typing import Dict, List, Any
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from app.db.models import Project, ProjectDependency, Package, Vulnerability, HealthReport
from app.services.ml.risk_models import FutureRiskPredictor


class RiskTimelineService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.predictor = FutureRiskPredictor()
    
    async def generate_timeline(self, project_id: UUID, days: int = 90) -> Dict[str, Any]:
        project = await self.db.get(Project, project_id)
        if not project:
            raise ValueError("Project not found")
        
        deps_query = select(ProjectDependency).where(
            ProjectDependency.project_id == project_id
        ).options(selectinload(ProjectDependency.package))
        
        result = await self.db.execute(deps_query)
        dependencies = result.scalars().all()
        
        package_risks = []
        
        for dep in dependencies:
            if not dep.package_id:
                continue
            
            package = await self.db.get(Package, dep.package_id)
            if not package:
                continue
            
            package_data = await self._collect_package_features(package)
            prediction = self.predictor.predict_future_risk(package_data, horizon_days=days)
            
            package_risks.append({
                "package_id": str(package.id),
                "package_name": package.name,
                "current_version": dep.version,
                "ecosystem": package.ecosystem.value,
                "is_direct": dep.is_direct,
                "current_risk": prediction["current_risk_score"],
                "projected_risk": prediction["projected_risk_score"],
                "trajectory": prediction["risk_trajectory"],
                "upgrade_timeline": prediction["upgrade_timeline"],
            })
        
        current_risk = self._calculate_project_risk(package_risks, "current")
        projected_risk = self._calculate_project_risk(package_risks, "projected")
        
        timeline_points = self._generate_timeline_points(
            package_risks,
            current_risk,
            projected_risk,
            days,
        )
        
        recommended_actions = self._generate_recommendations(package_risks)
        
        return {
            "project_id": str(project_id),
            "project_name": project.name,
            "generated_at": datetime.utcnow().isoformat(),
            "horizon_days": days,
            "current_risk": round(current_risk, 1),
            "projected_risk_30d": round(projected_risk, 1),
            "projected_risk_90d": round(projected_risk, 1),
            "timeline": timeline_points,
            "recommended_actions": recommended_actions,
            "package_risks": package_risks,
        }
    
    def _calculate_project_risk(self, package_risks: List[Dict], risk_type: str) -> float:
        if not package_risks:
            return 0.0
        
        total_risk = 0.0
        weight_sum = 0.0
        
        for pkg in package_risks:
            weight = 2.0 if pkg["is_direct"] else 1.0
            risk = pkg.get(f"{risk_type}_risk", 0)
            total_risk += risk * weight
            weight_sum += weight
        
        return total_risk / weight_sum if weight_sum > 0 else 0.0
    
    def _generate_timeline_points(
        self,
        package_risks: List[Dict],
        current_risk: float,
        projected_risk: float,
        days: int,
    ) -> List[Dict[str, Any]]:
        points = []
        num_points = min(days // 7, 12)
        
        for i in range(num_points + 1):
            day = (i * days) // num_points if num_points > 0 else 0
            date = datetime.utcnow() + timedelta(days=day)
            
            progress = i / num_points if num_points > 0 else 0
            risk = current_risk + (projected_risk - current_risk) * progress
            
            pkg_risks_at_day = []
            for pkg in package_risks:
                pkg_current = pkg["current_risk"]
                pkg_projected = pkg["projected_risk"]
                pkg_risk = pkg_current + (pkg_projected - pkg_current) * progress
                
                pkg_risks_at_day.append({
                    "package": pkg["package_name"],
                    "risk": round(pkg_risk, 1),
                })
            
            points.append({
                "day": day,
                "date": date.date().isoformat(),
                "projected_risk": round(risk, 1),
                "confidence": max(0.5, 1.0 - progress * 0.4),
                "package_risks": pkg_risks_at_day,
            })
        
        return points
    
    def _generate_recommendations(self, package_risks: List[Dict]) -> List[Dict[str, Any]]:
        recommendations = []
        
        for pkg in package_risks:
            current = pkg["current_risk"]
            projected = pkg["projected_risk"]
            timeline = pkg.get("upgrade_timeline", {})
            
            if timeline.get("immediate"):
                recommendations.append({
                    "priority": "critical",
                    "package": pkg["package_name"],
                    "action": "Upgrade immediately",
                    "reason": f"Critical vulnerability or active exploit detected. Current risk: {current:.0f}%",
                    "timeline_days": 0,
                    "effort": "high",
                })
            elif timeline.get("within_2_weeks"):
                recommendations.append({
                    "priority": "high",
                    "package": pkg["package_name"],
                    "action": "Upgrade within 2 weeks",
                    "reason": f"High severity vulnerability. Projected risk: {projected:.0f}%",
                    "timeline_days": 14,
                    "effort": "medium",
                })
            elif timeline.get("within_1_month"):
                recommendations.append({
                    "priority": "medium",
                    "package": pkg["package_name"],
                    "action": "Plan upgrade within 1 month",
                    "reason": f"Risk increasing. Projected risk: {projected:.0f}%",
                    "timeline_days": 30,
                    "effort": "low",
                })
            elif timeline.get("within_3_months"):
                recommendations.append({
                    "priority": "low",
                    "package": pkg["package_name"],
                    "action": "Schedule upgrade within 3 months",
                    "reason": f"Maintenance risk increasing risk is maintenance. Projected risk: {projected:.0f}%",
                    "timeline_days": 90,
                    "effort": "low",
                })
        
        recommendations.sort(key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["priority"], 4))
        
        return recommendations
    
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
        critical = [v for v in vulns if v.severity.value == "CRITICAL"]
        high = [v for v in vulns if v.severity.value == "HIGH"]
        
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
        
        download_trend = {"30d": 0, "90d": 0}
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