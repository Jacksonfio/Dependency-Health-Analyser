import enum
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, DateTime, ForeignKey, Enum, Index, 
    Boolean, Integer, JSON, UniqueConstraint, CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.db.session import Base


class Ecosystem(str, enum.Enum):
    NPM = "npm"
    MAVEN = "maven"
    PYPI = "pypi"
    DOCKER = "docker"
    GO = "go"
    NUGET = "nuget"
    CRATES = "crates"
    PUB = "pub"
    COMPOSER = "composer"
    COCOAPODS = "cocoapods"
    CARTHAGE = "carthage"
    SWIFTPM = "swiftpm"
    HEX = "hex"
    CPAN = "cpan"
    OPAM = "opam"
    CONAN = "conan"


class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class Package(Base):
    __tablename__ = "packages"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    ecosystem: Mapped[Ecosystem] = mapped_column(Enum(Ecosystem), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    homepage: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repository_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    license: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    downloads_last_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dependents_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    maintainers: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    vulnerabilities: Mapped[List["Vulnerability"]] = relationship(back_populates="package", lazy="dynamic")
    dependencies: Mapped[List["Dependency"]] = relationship(back_populates="package", lazy="dynamic", foreign_keys="Dependency.package_id")
    dependents: Mapped[List["Dependency"]] = relationship(back_populates="dependent", lazy="dynamic", foreign_keys="Dependency.dependent_id")
    health_scores: Mapped[List["HealthScore"]] = relationship(back_populates="package", lazy="dynamic")
    versions: Mapped[List["PackageVersion"]] = relationship(back_populates="package", lazy="dynamic")
    license_records: Mapped[List["LicenseRecord"]] = relationship(back_populates="package")


    
    __table_args__ = (
        UniqueConstraint("ecosystem", "name", "version", name="uq_package_ecosystem_name_version"),
        Index("ix_package_ecosystem_name", "ecosystem", "name"),
    )


class PackageVersion(Base):
    __tablename__ = "package_versions"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("packages.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deprecated: Mapped[bool] = mapped_column(Boolean, default=False)
    deprecation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    downloads: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    package: Mapped["Package"] = relationship(back_populates="versions")
    vulnerabilities: Mapped[List["Vulnerability"]] = relationship(back_populates="package_version", lazy="dynamic")
    dependencies: Mapped[List["Dependency"]] = relationship(back_populates="package_version", lazy="dynamic")
    
    __table_args__ = (
        UniqueConstraint("package_id", "version", name="uq_package_version"),
        Index("ix_package_version_package_id_version", "package_id", "version"),
    )


class Vulnerability(Base):
    __tablename__ = "vulnerabilities"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    cve_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    osv_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    ghsa_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    
    ecosystem: Mapped[Ecosystem] = mapped_column(Enum(Ecosystem), nullable=False, index=True)
    package_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    package_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("packages.id"), nullable=True, index=True)
    package_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("package_versions.id"), nullable=True, index=True)
    
    affected_versions: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    fixed_versions: Mapped[List[str]] = mapped_column(JSON, nullable=True)
    
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False, index=True)
    cvss_score: Mapped[Optional[float]] = mapped_column(nullable=True)
    cvss_vector: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    cwe_ids: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    references: Mapped[Optional[List[dict]]] = mapped_column(JSON, nullable=True)
    
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    package: Mapped[Optional["Package"]] = relationship(back_populates="vulnerabilities")
    package_version: Mapped[Optional["PackageVersion"]] = relationship(back_populates="vulnerabilities")
    health_scores: Mapped[List["HealthScore"]] = relationship(back_populates="vulnerability", lazy="dynamic")
    exploit_predictions: Mapped[List["ExploitPrediction"]] = relationship(back_populates="vulnerability", lazy="dynamic")
    fix_recommendations: Mapped[List["FixRecommendation"]] = relationship(back_populates="vulnerability", lazy="dynamic")
    
    __table_args__ = (
        Index("ix_vulnerability_ecosystem_package", "ecosystem", "package_name"),
        Index("ix_vulnerability_severity_published", "severity", "published_at"),
    )


class Dependency(Base):
    __tablename__ = "dependencies"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    
    package_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("packages.id"), nullable=False, index=True)
    dependent_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("packages.id"), nullable=False, index=True)
    package_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("package_versions.id"), nullable=True, index=True)
    
    version_requirement: Mapped[str] = mapped_column(String(100), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(50), nullable=False, default="runtime")
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dev: Mapped[bool] = mapped_column(Boolean, default=False)
    
    resolved_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_satisfied: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    package: Mapped["Package"] = relationship(back_populates="dependencies", foreign_keys=[package_id])
    dependent: Mapped["Package"] = relationship(back_populates="dependents", foreign_keys=[dependent_id])
    package_version: Mapped[Optional["PackageVersion"]] = relationship(back_populates="dependencies")
    
    __table_args__ = (
        UniqueConstraint("package_id", "dependent_id", "version_requirement", name="uq_dependency"),
        Index("ix_dependency_dependent_package", "dependent_id", "package_id"),
    )


class Project(Base):
    __tablename__ = "projects"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    repository_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repository_branch: Mapped[str] = mapped_column(String(100), default="main")
    
    ecosystem: Mapped[Ecosystem] = mapped_column(Enum(Ecosystem), nullable=False)
    package_manager: Mapped[str] = mapped_column(String(50), nullable=False)
    
    lockfile_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    lockfile_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_frequency: Mapped[str] = mapped_column(String(50), default="daily")
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=True, index=True)
    organization_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("organizations.id"), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    owner: Mapped[Optional["User"]] = relationship(back_populates="projects")
    organization: Mapped[Optional["Organization"]] = relationship(back_populates="projects")
    dependencies: Mapped[List["ProjectDependency"]] = relationship(back_populates="project", lazy="dynamic")
    scans: Mapped[List["Scan"]] = relationship(back_populates="project", lazy="dynamic")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="project", lazy="dynamic")
    health_reports: Mapped[List["HealthReport"]] = relationship(back_populates="project", lazy="dynamic")
    fix_prs: Mapped[List["FixPullRequest"]] = relationship(back_populates="project", lazy="dynamic")

    
    __table_args__ = (
        Index("ix_project_owner_ecosystem", "owner_id", "ecosystem"),
    )


class ProjectDependency(Base):
    __tablename__ = "project_dependencies"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("projects.id"), nullable=False, index=True)
    
    package_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("packages.id"), nullable=True, index=True)
    package_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("package_versions.id"), nullable=True, index=True)
    
    ecosystem: Mapped[Ecosystem] = mapped_column(Enum(Ecosystem), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    version_requirement: Mapped[str] = mapped_column(String(100), nullable=False)
    
    dependency_type: Mapped[str] = mapped_column(String(50), default="runtime")
    is_dev: Mapped[bool] = mapped_column(Boolean, default=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    
    is_direct: Mapped[bool] = mapped_column(Boolean, default=True)
    depth: Mapped[int] = mapped_column(Integer, default=0)
    path: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project: Mapped["Project"] = relationship(back_populates="dependencies")
    package: Mapped[Optional["Package"]] = relationship()
    package_version: Mapped[Optional["PackageVersion"]] = relationship()
    vulnerabilities: Mapped[List["ProjectDependencyVulnerability"]] = relationship(back_populates="project_dependency", lazy="dynamic")
    
    __table_args__ = (
        Index("ix_proj_dep_project_ecosystem_name", "project_id", "ecosystem", "name"),
    )


class ProjectDependencyVulnerability(Base):
    __tablename__ = "project_dependency_vulnerabilities"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    project_dependency_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("project_dependencies.id"), nullable=False, index=True)
    vulnerability_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("vulnerabilities.id"), nullable=False, index=True)
    
    is_direct: Mapped[bool] = mapped_column(Boolean, default=True)
    path: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    fixed_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    fixed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    project_dependency: Mapped["ProjectDependency"] = relationship(back_populates="vulnerabilities")
    vulnerability: Mapped["Vulnerability"] = relationship()


class Scan(Base):
    __tablename__ = "scans"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("projects.id"), nullable=False, index=True)
    
    status: Mapped[str] = mapped_column(String(50), default="pending")
    scan_type: Mapped[str] = mapped_column(String(50), default="full")
    
    total_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    vulnerable_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    
    lockfile_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    lockfile_changed: Mapped[bool] = mapped_column(Boolean, default=False)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    project: Mapped["Project"] = relationship(back_populates="scans")
    
    __table_args__ = (
        Index("ix_scan_project_started", "project_id", "started_at"),
    )


class HealthScore(Base):
    __tablename__ = "health_scores"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("packages.id"), nullable=False, index=True)
    vulnerability_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("vulnerabilities.id"), nullable=True, index=True)
    
    overall_score: Mapped[float] = mapped_column(nullable=False)
    maintenance_score: Mapped[float] = mapped_column(nullable=False)
    security_score: Mapped[float] = mapped_column(nullable=False)
    community_score: Mapped[float] = mapped_column(nullable=False)
    popularity_score: Mapped[float] = mapped_column(nullable=False)
    
    factors: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendations: Mapped[List[str]] = mapped_column(JSON, nullable=True)
    
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    package: Mapped["Package"] = relationship(back_populates="health_scores")
    vulnerability: Mapped[Optional["Vulnerability"]] = relationship(back_populates="health_scores")
    
    __table_args__ = (
        Index("ix_health_score_package_calculated", "package_id", "calculated_at"),
    )


class HealthReport(Base):
    __tablename__ = "health_reports"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("projects.id"), nullable=False, index=True)
    
    overall_score: Mapped[float] = mapped_column(nullable=False)
    security_score: Mapped[float] = mapped_column(nullable=False)
    maintenance_score: Mapped[float] = mapped_column(nullable=False)
    licensing_score: Mapped[float] = mapped_column(nullable=False)
    
    total_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    vulnerable_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    outdated_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    deprecated_dependencies: Mapped[int] = mapped_column(Integer, default=0)
    
    critical_vulns: Mapped[int] = mapped_column(Integer, default=0)
    high_vulns: Mapped[int] = mapped_column(Integer, default=0)
    medium_vulns: Mapped[int] = mapped_column(Integer, default=0)
    low_vulns: Mapped[int] = mapped_column(Integer, default=0)
    
    recommendations: Mapped[List[dict]] = mapped_column(JSON, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    
    project: Mapped["Project"] = relationship(back_populates="health_reports")
    
    __table_args__ = (
        Index("ix_health_report_project_generated", "project_id", "generated_at"),
    )


class Alert(Base):
    __tablename__ = "alerts"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("projects.id"), nullable=False, index=True)
    project_dependency_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("project_dependencies.id"), nullable=True, index=True)
    vulnerability_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), ForeignKey("vulnerabilities.id"), nullable=True, index=True)
    
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[Severity] = mapped_column(Enum(Severity), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid(), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    project: Mapped["Project"] = relationship(back_populates="alerts")
    project_dependency: Mapped[Optional["ProjectDependency"]] = relationship()
    vulnerability: Mapped[Optional["Vulnerability"]] = relationship()
    
    __table_args__ = (
        Index("ix_alert_project_created", "project_id", "created_at"),
        Index("ix_alert_severity_created", "severity", "created_at"),
    )


class FixRecommendation(Base):
    __tablename__ = "fix_recommendations"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    vulnerability_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("vulnerabilities.id"), nullable=False, index=True)
    
    fix_type: Mapped[str] = mapped_column(String(50), nullable=False)
    fixed_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    alternative_package: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    alternative_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    breaking_change: Mapped[bool] = mapped_column(Boolean, default=False)
    migration_effort: Mapped[str] = mapped_column(String(50), nullable=True)
    migration_guide_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    confidence_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    vulnerability: Mapped["Vulnerability"] = relationship(back_populates="fix_recommendations")


class ExploitPrediction(Base):
    __tablename__ = "exploit_predictions"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    vulnerability_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("vulnerabilities.id"), nullable=False, index=True)
    
    exploit_probability: Mapped[float] = mapped_column(nullable=False)
    time_to_exploit_days: Mapped[Optional[float]] = mapped_column(nullable=True)
    exploit_maturity: Mapped[str] = mapped_column(String(50), nullable=True)
    
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    features_used: Mapped[dict] = mapped_column(JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    
    vulnerability: Mapped["Vulnerability"] = relationship(back_populates="exploit_predictions")


class UserSetting(Base):
    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("users.id"), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="settings")

    __table_args__ = (
        UniqueConstraint("user_id", "section", "key", name="uq_user_setting"),
    )


class FixPullRequest(Base):
    __tablename__ = "fix_pull_requests"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("projects.id"), nullable=False, index=True)
    
    pr_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    status: Mapped[str] = mapped_column(String(50), default="pending")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    vulnerabilities_fixed: Mapped[List[uuid.UUID]] = mapped_column(JSON, nullable=True)
    dependencies_updated: Mapped[List[dict]] = mapped_column(JSON, nullable=True)
    
    base_branch: Mapped[str] = mapped_column(String(100), default="main")
    head_branch: Mapped[str] = mapped_column(String(100), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    project: Mapped["Project"] = relationship(back_populates="fix_prs")
    checks: Mapped[List["PRCheck"]] = relationship(back_populates="fix_pr", lazy="dynamic")


class PRCheck(Base):
    __tablename__ = "pr_checks"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    fix_pr_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("fix_pull_requests.id"), nullable=False, index=True)
    
    check_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    conclusion: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    fix_pr: Mapped["FixPullRequest"] = relationship(back_populates="checks")


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    
    github_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    github_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    github_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    projects: Mapped[List["Project"]] = relationship(back_populates="owner", primaryjoin="User.id == Project.owner_id")
    settings: Mapped[List["UserSetting"]] = relationship(back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    github_org_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    github_org_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    projects: Mapped[List["Project"]] = relationship(back_populates="organization", primaryjoin="Organization.id == Project.organization_id")


class LicenseRecord(Base):
    __tablename__ = "license_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    package_id: Mapped[uuid.UUID] = mapped_column(Uuid(), ForeignKey("packages.id"), nullable=False, index=True)
    spdx_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    compatibility: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    package: Mapped["Package"] = relationship(back_populates="license_records")

    __table_args__ = (
        UniqueConstraint("package_id", "spdx_id", name="uq_package_license"),
    )


