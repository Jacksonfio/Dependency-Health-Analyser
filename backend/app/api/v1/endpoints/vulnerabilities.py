from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Vulnerability, Severity, Package, Ecosystem
from app.schemas import VulnerabilityResponse, VulnerabilityDetailResponse, VulnerabilitySearchResponse
from app.services.scoring.engine import ScoringEngine

router = APIRouter()


@router.get("/search", response_model=VulnerabilitySearchResponse)
async def search_vulnerabilities(
    q: Optional[str] = None,
    cve_id: Optional[str] = None,
    ecosystem: Optional[Ecosystem] = None,
    package_name: Optional[str] = None,
    severity: Optional[Severity] = None,
    min_cvss: Optional[float] = Query(None, ge=0, le=10),
    max_cvss: Optional[float] = Query(None, ge=0, le=10),
    published_after: Optional[datetime] = None,
    published_before: Optional[datetime] = None,
    has_fix: Optional[bool] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Vulnerability)
    
    if q:
        query = query.where(
            or_(
                Vulnerability.cve_id.ilike(f"%{q}%"),
                Vulnerability.summary.ilike(f"%{q}%"),
                Vulnerability.details.ilike(f"%{q}%"),
            )
        )
    if cve_id:
        query = query.where(Vulnerability.cve_id == cve_id.upper())
    if ecosystem:
        query = query.where(Vulnerability.ecosystem == ecosystem)
    if package_name:
        query = query.where(Vulnerability.package_name.ilike(f"%{package_name}%"))
    if severity:
        query = query.where(Vulnerability.severity == severity)
    if min_cvss is not None:
        query = query.where(Vulnerability.cvss_score >= min_cvss)
    if max_cvss is not None:
        query = query.where(Vulnerability.cvss_score <= max_cvss)
    if published_after:
        query = query.where(Vulnerability.published_at >= published_after)
    if published_before:
        query = query.where(Vulnerability.published_at <= published_before)
    if has_fix is not None:
        if has_fix:
            query = query.where(Vulnerability.fixed_versions.isnot(None))
        else:
            query = query.where(Vulnerability.fixed_versions.is_(None))
    
    total_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(total_query)
    
    query = query.order_by(
        Vulnerability.cvss_score.desc().nullslast(),
        Vulnerability.published_at.desc().nullslast(),
    ).offset(offset).limit(limit)
    
    result = await db.execute(query)
    vulns = result.scalars().all()
    
    return VulnerabilitySearchResponse(
        items=[VulnerabilityResponse.model_validate(v) for v in vulns],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{vuln_id}", response_model=VulnerabilityDetailResponse)
async def get_vulnerability(
    vuln_id: UUID,
    include_exploit_prediction: bool = Query(False),
    include_fix_recommendation: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    query = select(Vulnerability).where(Vulnerability.id == vuln_id)
    query = query.options(selectinload(Vulnerability.package))
    
    if include_exploit_prediction:
        query = query.options(selectinload(Vulnerability.exploit_predictions))
    if include_fix_recommendation:
        query = query.options(selectinload(Vulnerability.fix_recommendations))
    
    result = await db.execute(query)
    vuln = result.scalar_one_or_none()
    
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    return VulnerabilityDetailResponse.model_validate(vuln)


@router.get("/{vuln_id}/exploit-prediction")
async def get_exploit_prediction(
    vuln_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.services.ml.exploit_predictor import ExploitPredictor
    
    vuln = await db.get(Vulnerability, vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    predictor = ExploitPredictor()
    prediction = await predictor.predict(vuln)
    
    return prediction


@router.get("/{vuln_id}/fix-recommendations")
async def get_fix_recommendations(
    vuln_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.services.ml.fix_recommender import FixRecommender
    
    vuln = await db.get(Vulnerability, vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    recommender = FixRecommender(db)
    recommendations = await recommender.get_recommendations(vuln)
    
    return {"recommendations": recommendations}


@router.get("/{vuln_id}/affected-packages")
async def get_affected_packages(
    vuln_id: UUID,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    vuln = await db.get(Vulnerability, vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    query = select(Package).where(
        and_(
            Package.ecosystem == vuln.ecosystem,
            Package.name == vuln.package_name,
        )
    ).limit(limit)
    
    result = await db.execute(query)
    packages = result.scalars().all()
    
    affected = []
    for pkg in packages:
        for version in vuln.affected_versions:
            if version in [v.version for v in pkg.versions]:
                affected.append({
                    "package_id": str(pkg.id),
                    "name": pkg.name,
                    "version": version,
                    "is_fixed": version in (vuln.fixed_versions or []),
                })
    
    return {"affected_packages": affected}


@router.get("/trending", response_model=List[VulnerabilityResponse])
async def get_trending_vulnerabilities(
    ecosystem: Optional[Ecosystem] = None,
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, le=100),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    query = select(Vulnerability).where(
        and_(
            Vulnerability.published_at >= cutoff,
            Vulnerability.severity.in_([Severity.CRITICAL, Severity.HIGH]),
        )
    )
    
    if ecosystem:
        query = query.where(Vulnerability.ecosystem == ecosystem)
    
    query = query.order_by(
        desc(Vulnerability.cvss_score.nullslast()),
        desc(Vulnerability.published_at),
    ).limit(limit)
    
    result = await db.execute(query)
    vulns = result.scalars().all()
    
    return [VulnerabilityResponse.model_validate(v) for v in vulns]


@router.get("/stats/summary")
async def get_vulnerability_stats(
    ecosystem: Optional[Ecosystem] = None,
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    
    query = select(
        Vulnerability.severity,
        func.count(Vulnerability.id).label("count")
    ).group_by(Vulnerability.severity)
    
    if ecosystem:
        query = query.where(Vulnerability.ecosystem == ecosystem)
    
    result = await db.execute(query)
    severity_counts = {row.severity.value: row.count for row in result}
    
    total = sum(severity_counts.values())
    
    recent_cutoff = datetime.utcnow() - timedelta(days=30)
    recent_query = select(func.count(Vulnerability.id)).where(
        Vulnerability.published_at >= recent_cutoff
    )
    if ecosystem:
        recent_query = recent_query.where(Vulnerability.ecosystem == ecosystem)
    recent_count = await db.scalar(recent_query)
    
    return {
        "total": total,
        "recent_30_days": recent_count,
        "by_severity": severity_counts,
        "ecosystem": ecosystem.value if ecosystem else "all",
    }