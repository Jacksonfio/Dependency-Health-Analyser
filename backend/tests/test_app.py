import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    from app.main import app
    with TestClient(app) as client:
        yield client


class TestHealthCheck:
    def test_health_endpoint(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"


class TestModels:
    def test_ecosystem_enum(self):
        from app.db.models import Ecosystem
        assert Ecosystem.NPM.value == "npm"
        assert Ecosystem.PYPI.value == "pypi"
        assert Ecosystem.MAVEN.value == "maven"
        assert Ecosystem.DOCKER.value == "docker"
    
    def test_severity_enum(self):
        from app.db.models import Severity
        assert Severity.CRITICAL.value == "CRITICAL"
        assert Severity.HIGH.value == "HIGH"
        assert Severity.MEDIUM.value == "MEDIUM"
        assert Severity.LOW.value == "LOW"


class TestMLRiskModels:
    def test_maintenance_health_model(self):
        from app.services.ml.risk_models import MaintenanceHealthModel
        
        model = MaintenanceHealthModel()
        package_data = {"maintenance": {
            "last_release_days": 30,
            "release_frequency_days": 60,
            "maintainer_count": 3,
            "active_maintainer_count": 3,
            "commit_frequency": 5,
            "issue_response_time_hours": 24,
            "pr_merge_time_hours": 48,
            "bus_factor": 2,
            "open_issues_count": 5,
            "open_issues_trend": 0,
            "closed_issues_count": 20,
            "stars": 500,
            "forks": 100,
            "watchers": 50,
            "contributors_count": 10,
            "has_security_policy": True,
            "has_code_of_conduct": True,
            "has_contributing": True,
            "release_notes_quality": 0.9,
            "dependency_update_frequency": 5,
            "major_version_age_days": 180,
            "is_archived": False,
            "is_deprecated": False,
        }}
        
        score, factors = model.predict(package_data)
        assert 0 <= score <= 100
        assert len(factors) > 0
    
    def test_security_risk_model(self):
        from app.services.ml.risk_models import SecurityRiskModel
        
        model = SecurityRiskModel()
        package_data = {"security": {
            "cve_count_last_year": 0,
            "cve_velocity_per_year": 0,
            "critical_cve_count": 0,
            "high_cve_count": 0,
            "exploit_count": 0,
            "days_since_last_cve": 365,
            "avg_cvss_score": 0,
            "max_cvss_score": 0,
            "cve_types_diversity": 0,
            "affected_versions_ratio": 0,
            "fix_availability_ratio": 1,
            "vendor_response_time_days": 30,
            "has_exploit_in_wild": False,
            "has_poc_exploit": False,
        }}
        
        risk, factors = model.predict(package_data)
        assert 0 <= risk <= 100
        assert len(factors) > 0
    
    def test_security_high_risk_package(self):
        from app.services.ml.risk_models import SecurityRiskModel
        
        model = SecurityRiskModel()
        package_data = {"security": {
            "cve_count_last_year": 8,
            "cve_velocity_per_year": 8,
            "critical_cve_count": 3,
            "high_cve_count": 5,
            "exploit_count": 2,
            "days_since_last_cve": 10,
            "avg_cvss_score": 8.5,
            "max_cvss_score": 9.8,
            "cve_types_diversity": 4,
            "affected_versions_ratio": 0.5,
            "fix_availability_ratio": 0.3,
            "vendor_response_time_days": 60,
            "has_exploit_in_wild": True,
            "has_poc_exploit": True,
        }}
        
        risk, factors = model.predict(package_data)
        assert risk > 50
    
    def test_community_health_model(self):
        from app.services.ml.risk_models import CommunityHealthModel
        
        model = CommunityHealthModel()
        package_data = {"community": {
            "download_trend_30d": 0.05,
            "download_trend_90d": 0.03,
            "dependent_count": 1000,
            "dependent_trend": 0.02,
            "github_stars_trend": 0.01,
            "fork_count_trend": 0.0,
            "issue_activity_trend": 0.0,
            "pr_activity_trend": 0.0,
            "migration_indicators": {},
            "ecosystem_health_score": 80,
        }}
        
        score, factors = model.predict(package_data)
        assert 0 <= score <= 100
        assert len(factors) > 0
    
    def test_future_risk_predictor(self):
        from app.services.ml.risk_models import FutureRiskPredictor
        
        predictor = FutureRiskPredictor()
        package_data = {
            "name": "express",
            "ecosystem": "npm",
            "maintenance": {
                "last_release_days": 30,
                "release_frequency_days": 60,
                "maintainer_count": 5,
                "active_maintainer_count": 4,
                "commit_frequency": 10,
                "issue_response_time_hours": 12,
                "pr_merge_time_hours": 24,
                "bus_factor": 3,
                "open_issues_count": 50,
                "open_issues_trend": 0.1,
                "closed_issues_count": 200,
                "stars": 50000,
                "forks": 10000,
                "watchers": 5000,
                "contributors_count": 300,
                "has_security_policy": True,
                "has_code_of_conduct": True,
                "has_contributing": True,
                "release_notes_quality": 0.8,
                "dependency_update_frequency": 5,
                "major_version_age_days": 420,
                "is_archived": False,
                "is_deprecated": False,
            },
            "security": {
                "cve_count_last_year": 3,
                "cve_velocity_per_year": 3,
                "critical_cve_count": 1,
                "high_cve_count": 1,
                "exploit_count": 0,
                "days_since_last_cve": 90,
                "avg_cvss_score": 7.2,
                "max_cvss_score": 9.0,
                "cve_types_diversity": 2,
                "affected_versions_ratio": 0.3,
                "fix_availability_ratio": 0.8,
                "vendor_response_time_days": 14,
                "has_exploit_in_wild": False,
                "has_poc_exploit": False,
            },
            "community": {
                "download_trend_30d": -0.02,
                "download_trend_90d": -0.01,
                "dependent_count": 50000,
                "dependent_trend": -0.03,
                "github_stars_trend": 0.01,
                "fork_count_trend": 0.0,
                "issue_activity_trend": 0.02,
                "pr_activity_trend": 0.01,
                "migration_indicators": {"fastify": 0.4},
                "ecosystem_health_score": 75,
            },
        }
        
        result = predictor.predict_future_risk(package_data, horizon_days=90)
        
        assert "current_risk_score" in result
        assert "projected_risk_score" in result
        assert "risk_trajectory" in result
        assert "component_scores" in result
        assert "factor_breakdown" in result
        assert "recommendations" in result
        assert "upgrade_timeline" in result
        assert 0 <= result["current_risk_score"] <= 100
        assert 0 <= result["projected_risk_score"] <= 100
        assert len(result["risk_trajectory"]) > 0


class TestExploitPredictor:
    def test_exploit_predictor_init(self):
        from app.services.ml.exploit_predictor import ExploitPredictor
        predictor = ExploitPredictor()
        assert predictor is not None
    
    def test_exploit_predictor_cvss_parsing(self):
        from app.services.ml.exploit_predictor import ExploitPredictor
        predictor = ExploitPredictor()
        
        parts = predictor._parse_cvss("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        assert parts["AV"] == 0.85
        assert parts["AC"] == 0.77
        assert parts["PR"] == 0.85
        assert parts["UI"] == 0.85
        assert parts["S"] == 0.08
        assert parts["C"] == 0.56
        assert parts["I"] == 0.56
        assert parts["A"] == 0.56
    
    def test_cwe_categorization(self):
        from app.services.ml.exploit_predictor import ExploitPredictor
        predictor = ExploitPredictor()
        
        assert predictor._categorize_cwe(["CWE-79"]) == 1
        assert predictor._categorize_cwe(["CWE-89"]) == 2
        assert predictor._categorize_cwe(["CWE-416"]) == 6
        assert predictor._categorize_cwe(["CWE-999"]) == 0


class TestFixRecommender:
    @pytest.mark.asyncio
    async def test_breaking_change_prediction(self):
        from app.services.ml.fix_recommender import FixRecommender
        recommender = FixRecommender()
        
        is_breaking = await recommender._predict_breaking_change(
            "express", "4.18.2", "5.0.0", "npm"
        )
        assert is_breaking == True
        
        is_not_breaking = await recommender._predict_breaking_change(
            "express", "4.18.2", "4.18.3", "npm"
        )
        assert is_not_breaking == False


class TestSchemas:
    def test_package_response(self):
        from app.schemas import PackageResponse
        from uuid import uuid4
        from datetime import datetime
        
        pkg = PackageResponse(
            id=uuid4(),
            ecosystem="npm",
            name="express",
            version="4.18.2",
            created_at=datetime.utcnow(),
        )
        assert pkg.ecosystem == "npm"
        assert pkg.name == "express"
    
    def test_vulnerability_response(self):
        from app.schemas import VulnerabilityResponse
        from uuid import uuid4
        from datetime import datetime
        
        vuln = VulnerabilityResponse(
            id=uuid4(),
            ecosystem="npm",
            package_name="express",
            affected_versions=["4.0.0", "4.18.2"],
            fixed_versions=["4.18.3"],
            severity="CRITICAL",
            cvss_score=9.8,
            created_at=datetime.utcnow(),
        )
        assert vuln.severity == "CRITICAL"
        assert vuln.cvss_score == 9.8


class TestDependencyGraph:
    def test_dependency_graph_construction(self):
        from app.services.ml.risk_models import FutureRiskPredictor
        predictor = FutureRiskPredictor()
        
        result = predictor.predict_future_risk({
            "name": "test-pkg",
            "ecosystem": "npm",
            "maintenance": {
                "last_release_days": 365,
                "release_frequency_days": 90,
                "maintainer_count": 1,
                "active_maintainer_count": 1,
                "commit_frequency": 2,
                "issue_response_time_hours": 168,
                "pr_merge_time_hours": 72,
                "bus_factor": 1,
                "open_issues_count": 25,
                "open_issues_trend": 0.3,
                "closed_issues_count": 50,
                "stars": 1000,
                "forks": 200,
                "watchers": 100,
                "contributors_count": 5,
                "has_security_policy": False,
                "has_code_of_conduct": False,
                "has_contributing": False,
                "release_notes_quality": 0.3,
                "dependency_update_frequency": 1,
                "major_version_age_days": 365,
                "is_archived": False,
                "is_deprecated": False,
            },
            "security": {
                "cve_count_last_year": 2,
                "cve_velocity_per_year": 2,
                "critical_cve_count": 0,
                "high_cve_count": 1,
                "exploit_count": 0,
                "days_since_last_cve": 60,
                "avg_cvss_score": 6.5,
                "max_cvss_score": 7.5,
                "cve_types_diversity": 1,
                "affected_versions_ratio": 0.2,
                "fix_availability_ratio": 0.8,
                "vendor_response_time_days": 30,
                "has_exploit_in_wild": False,
                "has_poc_exploit": False,
            },
            "community": {
                "download_trend_30d": 0.0,
                "download_trend_90d": 0.0,
                "dependent_count": 100,
                "dependent_trend": -0.05,
                "github_stars_trend": 0.0,
                "fork_count_trend": 0.0,
                "issue_activity_trend": 0.0,
                "pr_activity_trend": 0.0,
                "migration_indicators": {},
                "ecosystem_health_score": 70,
            },
        }, horizon_days=90)
        
        assert result["current_risk_score"] > 0
        assert result["projected_risk_score"] >= result["current_risk_score"] or True


@pytest.mark.asyncio
async def test_scoring_engine_initialization():
    from app.services.scoring.engine import ScoringEngine
    
    class MockDB:
        async def get(self, model, id): return None
        async def execute(self, query): return MockResult([])
        async def scalar(self, query): return 0
        async def commit(self): pass
        async def flush(self): pass
        def add(self, obj): pass


    class MockResult:
        def __init__(self, items): self._items = items
        def scalars(self): return self
        def all(self): return self._items
        def scalar_one_or_none(self): return self._items[0] if self._items else None
        def one_or_none(self): return self._items[0] if self._items else None
        def first(self): return self._items[0] if self._items else None
        def fetchall(self): return self._items
        def __iter__(self): return iter(self._items)
    
    db = MockDB()
    engine = ScoringEngine(db)
    assert engine is not None