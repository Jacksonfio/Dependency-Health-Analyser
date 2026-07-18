from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import Package, Project, UserSetting
from app.services.ml.data_collector import collect_package_features
from app.services.ml.risk_engine import compute_all_risks
from app.services.ml.risk_predictor import predict_risk, get_feature_importance
from app.services.ml.explainer import generate_explanation
from sqlalchemy import select
import json
import uuid
import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/risk-prediction", tags=["risk-prediction"])


@router.get("/package/{package_id}")
async def predict_package_risk(package_id: str, db: AsyncSession = Depends(get_db)):
    try:
        pkg_uuid = uuid.UUID(package_id)
    except ValueError:
        raise HTTPException(404, "Package not found")
    
    q = select(Package).where(Package.id == pkg_uuid)
    result = await db.execute(q)
    pkg = result.scalar_one_or_none()
    if not pkg:
        raise HTTPException(404, "Package not found")

    from app.db.models import ProjectDependency
    q2 = select(ProjectDependency).where(ProjectDependency.package_id == pkg_uuid)
    r2 = await db.execute(q2)
    pd = r2.scalar_one_or_none()

    ecosystem = "npm"
    if pd:
        q3 = select(Project).where(Project.id == pd.project_id)
        r3 = await db.execute(q3)
        proj = r3.scalar_one_or_none()
        if proj:
            ecosystem = proj.ecosystem or "npm"
    else:
        ecosystem = pkg.ecosystem or "npm"

    github_token = ""
    sq = select(UserSetting).where(UserSetting.key == "github_token", UserSetting.section == "api_keys")
    sr = await db.execute(sq)
    st = sr.scalar_one_or_none()
    if st:
        try:
            v = json.loads(st.value)
            github_token = v.get("value", "")
        except:
            pass

    try:
        features = await collect_package_features(pkg.name, ecosystem, github_token)
        risk_result = compute_all_risks(features)
        ml_result = predict_risk(features)
        importance = get_feature_importance(features)
        explanation = generate_explanation(features, risk_result, ml_result)
    except Exception as e:
        logger.exception("Risk prediction failed")
        raise HTTPException(500, f"Risk prediction failed: {str(e)}")

    return {
        "package": {"id": pkg.id, "name": pkg.name, "ecosystem": ecosystem},
        "features": features,
        "risk_factors": risk_result["factors"],
        "combined_score": risk_result["overall_risk"],
        "breakdown": risk_result["breakdown"],
        "ml_prediction": ml_result,
        "explanation": explanation,
        "feature_importance": importance,
    }


@router.get("/by-name/{ecosystem}/{package_name:path}")
async def predict_by_name(ecosystem: str, package_name: str, db: AsyncSession = Depends(get_db)):
    pkg_name_lower = package_name.lower()
    q = select(Package).where(Package.name == pkg_name_lower)
    result = await db.execute(q)
    pkg = result.scalar_one_or_none()

    if not pkg:
        raise HTTPException(404, f"Package '{package_name}' not found in database. Run a live scan first.")

    return await predict_package_risk(pkg.id, db)
