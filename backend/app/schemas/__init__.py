from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class PackageResponse(BaseModel):
    id: UUID
    ecosystem: str
    name: str
    version: str
    description: Optional[str] = None
    homepage: Optional[str] = None
    repository_url: Optional[str] = None
    license: Optional[str] = None
    keywords: Optional[List[str]] = None
    downloads_last_month: Optional[int] = None
    dependents_count: Optional[int] = None
    maintainers: Optional[List[Dict[str, Any]]] = None
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PackageDetailResponse(PackageResponse):
    pass


class VulnerabilityResponse(BaseModel):
    id: UUID
    cve_id: Optional[str] = None
    ecosystem: str
    package_name: str
    affected_versions: List[str]
    fixed_versions: Optional[List[str]] = None
    summary: Optional[str] = None
    severity: str
    cvss_score: Optional[float] = None
    published_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VulnerabilityDetailResponse(VulnerabilityResponse):
    pass


class ScanResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    scan_type: str
    total_dependencies: int = 0
    vulnerable_dependencies: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ScanDetailResponse(ScanResponse):
    pass


class HealthScoreResponse(BaseModel):
    id: UUID
    package_id: UUID
    overall_score: float
    maintenance_score: float
    security_score: float
    community_score: float
    popularity_score: float
    factors: Dict[str, Any]
    recommendations: Optional[List[str]] = None
    calculated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HealthReportResponse(BaseModel):
    id: UUID
    project_id: UUID
    overall_score: float
    security_score: float
    maintenance_score: float
    licensing_score: float
    total_dependencies: int = 0
    vulnerable_dependencies: int = 0
    critical_vulns: int = 0
    high_vulns: int = 0
    medium_vulns: int = 0
    low_vulns: int = 0
    generated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    repository_url: Optional[str] = None
    ecosystem: str
    package_manager: str
    is_monitored: bool = True
    last_scanned_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectDetailResponse(ProjectResponse):
    pass


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    ecosystem: str
    package_manager: str
    repository_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    repository_url: Optional[str] = None
    is_monitored: Optional[bool] = None


class AlertResponse(BaseModel):
    id: UUID
    project_id: UUID
    alert_type: str
    severity: str
    title: str
    message: str
    is_read: bool = False
    is_dismissed: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardStatsResponse(BaseModel):
    total_projects: int = 0
    total_dependencies: int = 0
    critical_vulns: int = 0
    high_vulns: int = 0
    medium_vulns: int = 0
    low_vulns: int = 0
    avg_health_score: float = 0


class PackageSearchResponse(BaseModel):
    items: List[PackageResponse] = []
    total: int = 0
    limit: int = 20
    offset: int = 0


class VulnerabilitySearchResponse(BaseModel):
    items: List[VulnerabilityResponse] = []
    total: int = 0
    limit: int = 50
    offset: int = 0


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse] = []
    total: int = 0
    limit: int = 20
    offset: int = 0