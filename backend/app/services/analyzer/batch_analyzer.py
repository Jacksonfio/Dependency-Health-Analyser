from app.services.ml.data_collector import collect_package_features
from app.services.ml.risk_engine import compute_all_risks
from app.services.ml.risk_predictor import predict_risk
from app.services.ml.explainer import generate_explanation
import asyncio
import logging

logger = logging.getLogger(__name__)


async def analyze_dependency(name: str, ecosystem: str, github_token: str = "") -> dict:
    try:
        features = await collect_package_features(name, ecosystem, github_token)
        risk = compute_all_risks(features)
        ml = predict_risk(features)
        exp = generate_explanation(features, risk, ml)
        return {
            "name": name,
            "ecosystem": ecosystem,
            "risk_score": risk["overall_risk"],
            "risk_level": exp["risk_level"],
            "factors": risk["factors"],
            "ml_prediction": ml,
            "explanation": exp,
            "features": features,
        }
    except Exception as e:
        logger.warning(f"Failed to analyze {name}: {e}")
        return {
            "name": name,
            "ecosystem": ecosystem,
            "risk_score": None,
            "risk_level": "unknown",
            "factors": [],
            "ml_prediction": {},
            "explanation": {"risk_level": "unknown", "key_factors": [], "warning": [], "recommendations": ["Failed to fetch data"]},
            "features": {},
            "error": str(e),
        }


async def batch_analyze(dependencies: list, github_token: str = "") -> dict:
    tasks = []
    for dep in dependencies:
        tasks.append(analyze_dependency(dep["name"], dep.get("ecosystem", "npm"), github_token))

    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x.get("risk_score") or 0, reverse=True)

    avg_risk = 0
    count = 0
    for r in results:
        if r.get("risk_score") is not None:
            avg_risk += r["risk_score"]
            count += 1
    avg_risk = round(avg_risk / count, 1) if count > 0 else 0

    critical = sum(1 for r in results if r.get("risk_level") == "critical")
    high = sum(1 for r in results if r.get("risk_level") == "high")
    medium = sum(1 for r in results if r.get("risk_level") == "medium")
    low = sum(1 for r in results if r.get("risk_level") == "low")

    return {
        "summary": {
            "total_dependencies": len(results),
            "average_risk": avg_risk,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "urgent_upgrades": critical + high,
        },
        "results": results,
    }
