import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import joblib
import os
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class MaintenanceFeatures:
    last_release_days: float
    release_frequency_days: float
    maintainer_count: int
    active_maintainer_count: int
    commit_frequency: float
    issue_response_time_hours: float
    pr_merge_time_hours: float
    bus_factor: int
    open_issues_count: int
    open_issues_trend: float
    closed_issues_count: int
    stars: int
    forks: int
    watchers: int
    contributors_count: int
    has_security_policy: bool
    has_code_of_conduct: bool
    has_contributing: bool
    release_notes_quality: float
    dependency_update_frequency: float
    major_version_age_days: float
    is_archived: bool
    is_deprecated: bool


@dataclass
class SecurityFeatures:
    cve_count_last_year: int
    cve_velocity_per_year: float
    critical_cve_count: int
    high_cve_count: int
    exploit_count: int
    days_since_last_cve: float
    avg_cvss_score: float
    max_cvss_score: float
    cve_types_diversity: int
    affected_versions_ratio: float
    fix_availability_ratio: float
    vendor_response_time_days: float
    has_exploit_in_wild: bool
    has_poc_exploit: bool


@dataclass
class CommunityFeatures:
    download_trend_30d: float
    download_trend_90d: float
    dependent_count: int
    dependent_trend: float
    github_stars_trend: float
    fork_count_trend: float
    issue_activity_trend: float
    pr_activity_trend: float
    migration_indicators: Dict[str, float]
    ecosystem_health_score: float


@dataclass
class PackageFeatures:
    maintenance: MaintenanceFeatures
    security: SecurityFeatures
    community: CommunityFeatures


class MaintenanceHealthModel:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.path.join(settings.ml_model_path, "maintenance_model.pkl")
        self.model = None
        self.scaler = None
        self._load_model()
    
    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                artifacts = joblib.load(self.model_path)
                self.model = artifacts["model"]
                self.scaler = artifacts["scaler"]
                logger.info("Loaded maintenance health model")
            except Exception as e:
                logger.warning(f"Failed to load maintenance model: {e}")
                self._create_default_model()
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        logger.info("Created default maintenance model")
    
    def extract_features(self, package_data: Dict[str, Any]) -> np.ndarray:
        m = package_data.get("maintenance", {})
        
        features = [
            m.get("last_release_days", 365),
            m.get("release_frequency_days", 90),
            m.get("maintainer_count", 1),
            m.get("active_maintainer_count", 1),
            m.get("commit_frequency", 0),
            m.get("issue_response_time_hours", 720),
            m.get("pr_merge_time_hours", 168),
            m.get("bus_factor", 1),
            m.get("open_issues_count", 0),
            m.get("open_issues_trend", 0),
            m.get("closed_issues_count", 0),
            m.get("stars", 0),
            m.get("forks", 0),
            m.get("watchers", 0),
            m.get("contributors_count", 1),
            float(m.get("has_security_policy", False)),
            float(m.get("has_code_of_conduct", False)),
            float(m.get("has_contributing", False)),
            m.get("release_notes_quality", 0.5),
            m.get("dependency_update_frequency", 0),
            m.get("major_version_age_days", 365),
            float(m.get("is_archived", False)),
            float(m.get("is_deprecated", False)),
        ]
        
        return np.array(features).reshape(1, -1)
    
    def predict(self, package_data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        features = self.extract_features(package_data)
        
        if self.model is not None and self.scaler is not None:
            try:
                features_scaled = self.scaler.transform(features)
                score = self.model.predict(features_scaled)[0]
                score = max(0, min(100, score))
            except Exception as e:
                logger.warning(f"Model prediction failed, using heuristic: {e}")
                score = self._heuristic_score(package_data)
        else:
            score = self._heuristic_score(package_data)
        
        factors = self._compute_factor_scores(package_data)
        
        return score, factors
    
    def _heuristic_score(self, package_data: Dict[str, Any]) -> float:
        m = package_data.get("maintenance", {})
        
        score = 100.0
        
        last_release = m.get("last_release_days", 365)
        if last_release > 365:
            score -= 30
        elif last_release > 180:
            score -= 15
        elif last_release > 90:
            score -= 5
        
        maintainer_count = m.get("active_maintainer_count", 1)
        if maintainer_count == 0:
            score -= 40
        elif maintainer_count == 1:
            score -= 15
        
        bus_factor = m.get("bus_factor", 1)
        if bus_factor == 1:
            score -= 10
        
        issue_response = m.get("issue_response_time_hours", 720)
        if issue_response > 720:
            score -= 10
        elif issue_response > 168:
            score -= 5
        
        open_issues_trend = m.get("open_issues_trend", 0)
        if open_issues_trend > 0.5:
            score -= 10
        elif open_issues_trend > 0.2:
            score -= 5
        
        if m.get("is_archived", False):
            score -= 50
        if m.get("is_deprecated", False):
            score -= 50
        
        return max(0, min(100, score))
    
    def _compute_factor_scores(self, package_data: Dict[str, Any]) -> Dict[str, float]:
        m = package_data.get("maintenance", {})
        
        return {
            "release_recency": max(0, 100 - m.get("last_release_days", 365) / 3.65),
            "maintainer_activity": min(100, m.get("active_maintainer_count", 1) * 25),
            "bus_factor": min(100, m.get("bus_factor", 1) * 33),
            "issue_responsiveness": max(0, 100 - m.get("issue_response_time_hours", 720) / 7.2),
            "pr_responsiveness": max(0, 100 - m.get("pr_merge_time_hours", 168) / 1.68),
            "issue_management": max(0, 100 - m.get("open_issues_trend", 0) * 100),
            "community_health": min(100, (m.get("stars", 0) + m.get("forks", 0)) / 10),
            "governance": (
                float(m.get("has_security_policy", False)) * 33 +
                float(m.get("has_code_of_conduct", False)) * 33 +
                float(m.get("has_contributing", False)) * 34
            ),
            "archived_penalty": -50 if m.get("is_archived", False) else 0,
            "deprecated_penalty": -50 if m.get("is_deprecated", False) else 0,
        }
    
    def train(self, training_data: List[Dict[str, Any]], labels: List[float]):
        X = np.array([self.extract_features(d).flatten() for d in training_data])
        y = np.array(labels)
        
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        self.model.fit(X_train_scaled, y_train)
        
        val_score = self.model.score(X_val_scaled, y_val)
        logger.info(f"Maintenance model validation R²: {val_score:.3f}")
        
        self.save()
    
    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
        }, self.model_path)


class SecurityRiskModel:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.path.join(settings.ml_model_path, "security_model.pkl")
        self.model = None
        self.scaler = None
        self._load_model()
    
    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                artifacts = joblib.load(self.model_path)
                self.model = artifacts["model"]
                self.scaler = artifacts["scaler"]
                logger.info("Loaded security risk model")
            except Exception as e:
                logger.warning(f"Failed to load security model: {e}")
                self._create_default_model()
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.preprocessing import StandardScaler
        
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42
        )
        self.scaler = StandardScaler()
        logger.info("Created default security model")
    
    def extract_features(self, package_data: Dict[str, Any]) -> np.ndarray:
        s = package_data.get("security", {})
        
        features = [
            s.get("cve_count_last_year", 0),
            s.get("cve_velocity_per_year", 0),
            s.get("critical_cve_count", 0),
            s.get("high_cve_count", 0),
            s.get("exploit_count", 0),
            s.get("days_since_last_cve", 365),
            s.get("avg_cvss_score", 0),
            s.get("max_cvss_score", 0),
            s.get("cve_types_diversity", 0),
            s.get("affected_versions_ratio", 0),
            s.get("fix_availability_ratio", 1),
            s.get("vendor_response_time_days", 30),
            float(s.get("has_exploit_in_wild", False)),
            float(s.get("has_poc_exploit", False)),
        ]
        
        return np.array(features).reshape(1, -1)
    
    def predict(self, package_data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        features = self.extract_features(package_data)
        
        if self.model is not None and self.scaler is not None:
            try:
                features_scaled = self.scaler.transform(features)
                risk_score = self.model.predict(features_scaled)[0]
                risk_score = max(0, min(100, risk_score))
            except Exception as e:
                logger.warning(f"Security model prediction failed: {e}")
                risk_score = self._heuristic_score(package_data)
        else:
            risk_score = self._heuristic_score(package_data)
        
        factors = self._compute_factor_scores(package_data)
        
        return risk_score, factors
    
    def _heuristic_score(self, package_data: Dict[str, Any]) -> float:
        s = package_data.get("security", {})
        
        score = 0.0
        
        critical = s.get("critical_cve_count", 0)
        high = s.get("high_cve_count", 0)
        medium = s.get("cve_count_last_year", 0) - critical - high
        
        score += critical * 25
        score += high * 15
        score += medium * 5
        
        if s.get("has_exploit_in_wild", False):
            score += 30
        if s.get("has_poc_exploit", False):
            score += 15
        
        days_since = s.get("days_since_last_cve", 365)
        if days_since < 30:
            score += 10
        elif days_since < 90:
            score += 5
        
        velocity = s.get("cve_velocity_per_year", 0)
        if velocity > 10:
            score += 15
        elif velocity > 5:
            score += 10
        
        fix_ratio = s.get("fix_availability_ratio", 1)
        if fix_ratio < 0.5:
            score += 20
        elif fix_ratio < 0.8:
            score += 10
        
        return min(100, score)
    
    def _compute_factor_scores(self, package_data: Dict[str, Any]) -> Dict[str, float]:
        s = package_data.get("security", {})
        
        return {
            "cve_severity": min(100, s.get("critical_cve_count", 0) * 25 + s.get("high_cve_count", 0) * 15),
            "exploit_risk": 30 if s.get("has_exploit_in_wild") else (15 if s.get("has_poc_exploit") else 0),
            "cve_velocity": min(100, s.get("cve_velocity_per_year", 0) * 10),
            "fix_availability": (1 - s.get("fix_availability_ratio", 1)) * 100,
            "recency": max(0, 100 - s.get("days_since_last_cve", 365) / 3.65),
            "vendor_response": max(0, 100 - s.get("vendor_response_time_days", 30) * 3.33),
        }
    
    def train(self, training_data: List[Dict[str, Any]], labels: List[float]):
        X = np.array([self.extract_features(d).flatten() for d in training_data])
        y = np.array(labels)
        
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        self.model.fit(X_train_scaled, y_train)
        
        val_score = self.model.score(X_val_scaled, y_val)
        logger.info(f"Security model validation R²: {val_score:.3f}")
        
        self.save()
    
    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
        }, self.model_path)


class CommunityHealthModel:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or os.path.join(settings.ml_model_path, "community_model.pkl")
        self.model = None
        self.scaler = None
        self._load_model()
    
    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                artifacts = joblib.load(self.model_path)
                self.model = artifacts["model"]
                self.scaler = artifacts["scaler"]
                logger.info("Loaded community health model")
            except Exception as e:
                logger.warning(f"Failed to load community model: {e}")
                self._create_default_model()
        else:
            self._create_default_model()
    
    def _create_default_model(self):
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.preprocessing import StandardScaler
        
        self.model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        self.scaler = StandardScaler()
        logger.info("Created default community model")
    
    def extract_features(self, package_data: Dict[str, Any]) -> np.ndarray:
        c = package_data.get("community", {})
        
        features = [
            c.get("download_trend_30d", 0),
            c.get("download_trend_90d", 0),
            c.get("dependent_count", 0),
            c.get("dependent_trend", 0),
            c.get("github_stars_trend", 0),
            c.get("fork_count_trend", 0),
            c.get("issue_activity_trend", 0),
            c.get("pr_activity_trend", 0),
            c.get("ecosystem_health_score", 50),
        ]
        
        migration = c.get("migration_indicators", {})
        for key in sorted(migration.keys()):
            features.append(migration[key])
        
        return np.array(features).reshape(1, -1)
    
    def predict(self, package_data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        features = self.extract_features(package_data)
        
        if self.model is not None and self.scaler is not None:
            try:
                features_scaled = self.scaler.transform(features)
                score = self.model.predict(features_scaled)[0]
                score = max(0, min(100, score))
            except Exception as e:
                logger.warning(f"Community model prediction failed: {e}")
                score = self._heuristic_score(package_data)
        else:
            score = self._heuristic_score(package_data)
        
        factors = self._compute_factor_scores(package_data)
        
        return score, factors
    
    def _heuristic_score(self, package_data: Dict[str, Any]) -> float:
        c = package_data.get("community", {})
        
        score = 50.0
        
        dep_trend = c.get("dependent_trend", 0)
        if dep_trend < -0.2:
            score -= 20
        elif dep_trend < 0:
            score -= 10
        elif dep_trend > 0.2:
            score += 10
        
        stars_trend = c.get("github_stars_trend", 0)
        if stars_trend < -0.1:
            score -= 10
        elif stars_trend > 0.1:
            score += 5
        
        migration = c.get("migration_indicators", {})
        for alt, strength in migration.items():
            if strength > 0.7:
                score -= 25
            elif strength > 0.4:
                score -= 10
        
        eco_health = c.get("ecosystem_health_score", 50)
        score = score * 0.5 + eco_health * 0.5
        
        return max(0, min(100, score))
    
    def _compute_factor_scores(self, package_data: Dict[str, Any]) -> Dict[str, float]:
        c = package_data.get("community", {})
        
        return {
            "adoption_trend": max(0, min(100, 50 + c.get("dependent_trend", 0) * 250)),
            "github_interest": max(0, min(100, 50 + c.get("github_stars_trend", 0) * 250)),
            "migration_risk": max(0, min(100, max(c.get("migration_indicators", {}).values(), default=0) * 100)),
            "ecosystem_health": c.get("ecosystem_health_score", 50),
            "download_momentum": max(0, min(100, 50 + c.get("download_trend_90d", 0) * 100)),
        }
    
    def train(self, training_data: List[Dict[str, Any]], labels: List[float]):
        X = np.array([self.extract_features(d).flatten() for d in training_data])
        y = np.array(labels)
        
        from sklearn.model_selection import train_test_split
        from sklearn.preprocessing import StandardScaler
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        self.model.fit(X_train_scaled, y_train)
        
        val_score = self.model.score(X_val_scaled, y_val)
        logger.info(f"Community model validation R²: {val_score:.3f}")
        
        self.save()
    
    def save(self):
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
        }, self.model_path)


class FutureRiskPredictor:
    def __init__(self):
        self.maintenance_model = MaintenanceHealthModel()
        self.security_model = SecurityRiskModel()
        self.community_model = CommunityHealthModel()
    
    def predict_future_risk(
        self,
        package_data: Dict[str, Any],
        horizon_days: int = 90,
    ) -> Dict[str, Any]:
        maintenance_score, maint_factors = self.maintenance_model.predict(package_data)
        security_score, sec_factors = self.security_model.predict(package_data)
        community_score, comm_factors = self.community_model.predict(package_data)
        
        current_risk = (
            (100 - maintenance_score) * 0.35 +
            security_score * 0.45 +
            (100 - community_score) * 0.20
        )
        
        projected_risk = self._project_risk(
            current_risk,
            maintenance_score,
            security_score,
            community_score,
            horizon_days,
            package_data,
        )
        
        risk_trajectory = self._generate_trajectory(
            current_risk,
            projected_risk,
            horizon_days,
            package_data,
        )
        
        recommendations = self._generate_recommendations(
            maintenance_score,
            security_score,
            community_score,
            maint_factors,
            sec_factors,
            comm_factors,
        )
        
        upgrade_timeline = self._calculate_upgrade_timeline(
            current_risk,
            projected_risk,
            package_data,
        )
        
        return {
            "current_risk_score": round(current_risk, 1),
            "projected_risk_score": round(projected_risk, 1),
            "horizon_days": horizon_days,
            "risk_trajectory": risk_trajectory,
            "component_scores": {
                "maintenance": round(maintenance_score, 1),
                "security": round(100 - security_score, 1),
                "community": round(community_score, 1),
            },
            "factor_breakdown": {
                "maintenance": maint_factors,
                "security": sec_factors,
                "community": comm_factors,
            },
            "recommendations": recommendations,
            "upgrade_timeline": upgrade_timeline,
            "confidence": self._calculate_confidence(package_data),
            "generated_at": datetime.utcnow().isoformat(),
        }
    
    def _project_risk(
        self,
        current_risk: float,
        maintenance_score: float,
        security_score: float,
        community_score: float,
        horizon_days: int,
        package_data: Dict[str, Any],
    ) -> float:
        m = package_data.get("maintenance", {})
        s = package_data.get("security", {})
        c = package_data.get("community", {})
        
        risk_delta = 0.0
        
        last_release = m.get("last_release_days", 365)
        if last_release > 180:
            risk_delta += min(30, (last_release - 180) / 10)
        
        velocity = s.get("cve_velocity_per_year", 0)
        risk_delta += velocity * (horizon_days / 365) * 5
        
        dep_trend = c.get("dependent_trend", 0)
        if dep_trend < -0.1:
            risk_delta += abs(dep_trend) * 100
        
        migration = c.get("migration_indicators", {})
        max_migration = max(migration.values(), default=0)
        if max_migration > 0.5:
            risk_delta += max_migration * 30
        
        if m.get("is_archived", False) or m.get("is_deprecated", False):
            risk_delta += 40
        
        projected = min(100, current_risk + risk_delta)
        
        return projected
    
    def _generate_trajectory(
        self,
        current_risk: float,
        projected_risk: float,
        horizon_days: int,
        package_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        trajectory = []
        points = min(horizon_days // 7, 12)
        
        for i in range(points + 1):
            day = (i * horizon_days) // points
            progress = i / points if points > 0 else 0
            
            risk = current_risk + (projected_risk - current_risk) * progress
            
            trajectory.append({
                "day": day,
                "date": (datetime.utcnow() + timedelta(days=day)).date().isoformat(),
                "projected_risk": round(risk, 1),
                "confidence": max(0.5, 1.0 - progress * 0.4),
            })
        
        return trajectory
    
    def _generate_recommendations(
        self,
        maintenance_score: float,
        security_score: float,
        community_score: float,
        maint_factors: Dict[str, float],
        sec_factors: Dict[str, float],
        comm_factors: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        recommendations = []
        
        if maintenance_score < 50:
            recommendations.append({
                "type": "maintenance",
                "priority": "high" if maintenance_score < 30 else "medium",
                "title": "Maintainer activity declining",
                "description": f"Maintenance health score is {maintenance_score:.0f}/100. Consider finding alternatives or forking.",
                "actions": [
                    "Monitor maintainer activity weekly",
                    "Prepare migration plan to alternative package",
                    "Consider forking if critical to your project",
                ],
                "timeline_days": 30 if maintenance_score < 30 else 90,
            })
        
        if security_score > 50:
            recommendations.append({
                "type": "security",
                "priority": "critical" if security_score > 75 else "high",
                "title": "Elevated security risk",
                "description": f"Security risk score is {security_score:.0f}/100. Immediate attention required.",
                "actions": [
                    "Upgrade to latest patched version immediately",
                    "Check for exploit availability",
                    "Apply workarounds if upgrade not possible",
                ],
                "timeline_days": 7 if security_score > 75 else 14,
            })
        
        if community_score < 40:
            recommendations.append({
                "type": "community",
                "priority": "medium",
                "title": "Community adoption declining",
                "description": f"Community health score is {community_score:.0f}/100. Migration may be needed.",
                "actions": [
                    "Evaluate alternative packages with stronger communities",
                    "Monitor for fork/maintained alternatives",
                    "Plan migration within 90 days",
                ],
                "timeline_days": 90,
            })
        
        if comm_factors.get("migration_risk", 0) > 50:
            recommendations.append({
                "type": "migration",
                "priority": "high",
                "title": "Active migration detected in ecosystem",
                "description": "Community is migrating to alternative packages.",
                "actions": [
                    "Identify recommended replacement",
                    "Begin migration planning",
                    "Test compatibility with alternative",
                ],
                "timeline_days": 60,
            })
        
        return recommendations
    
    def _calculate_upgrade_timeline(
        self,
        current_risk: float,
        projected_risk: float,
        package_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        s = package_data.get("security", {})
        m = package_data.get("maintenance", {})
        
        timeline = {
            "immediate": [],
            "within_2_weeks": [],
            "within_1_month": [],
            "within_3_months": [],
            "no_action_needed": [],
        }
        
        if s.get("critical_cve_count", 0) > 0 or s.get("has_exploit_in_wild", False):
            timeline["immediate"].append({
                "package": package_data.get("name", "unknown"),
                "reason": "Critical vulnerability or active exploit",
                "action": "Upgrade immediately",
            })
        elif s.get("high_cve_count", 0) > 0:
            timeline["within_2_weeks"].append({
                "package": package_data.get("name", "unknown"),
                "reason": "High severity vulnerabilities",
                "action": "Upgrade within 2 weeks",
            })
        elif m.get("last_release_days", 0) > 365:
            timeline["within_1_month"].append({
                "package": package_data.get("name", "unknown"),
                "reason": "No releases in over a year",
                "action": "Evaluate alternatives within 1 month",
            })
        elif projected_risk > 70:
            timeline["within_3_months"].append({
                "package": package_data.get("name", "unknown"),
                "reason": f"Projected risk score: {projected_risk:.0f}",
                "action": "Plan upgrade within 3 months",
            })
        else:
            timeline["no_action_needed"].append({
                "package": package_data.get("name", "unknown"),
                "reason": f"Risk stable at {current_risk:.0f}",
                "action": "Monitor regularly",
            })
        
        return timeline
    
    def _calculate_confidence(self, package_data: Dict[str, Any]) -> float:
        confidence = 0.5
        
        if package_data.get("maintenance", {}).get("last_release_days", 365) < 365:
            confidence += 0.1
        if package_data.get("security", {}).get("cve_count_last_year", 0) > 0:
            confidence += 0.1
        if package_data.get("community", {}).get("dependent_count", 0) > 100:
            confidence += 0.1
        if package_data.get("maintenance", {}).get("maintainer_count", 0) > 1:
            confidence += 0.1
        if package_data.get("maintenance", {}).get("stars", 0) > 1000:
            confidence += 0.1
        
        return min(0.95, confidence)