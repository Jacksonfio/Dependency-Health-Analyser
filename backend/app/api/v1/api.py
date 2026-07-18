from fastapi import APIRouter

from app.api.v1.endpoints import packages, vulnerabilities, projects, seed, settings, licenses, vulnerability_aging, impact_simulator, remediation, dashboard, live_scan, risk_prediction, analyze

api_router = APIRouter()

api_router.include_router(packages.router, prefix="/packages", tags=["packages"])
api_router.include_router(vulnerabilities.router, prefix="/vulnerabilities", tags=["vulnerabilities"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
api_router.include_router(licenses.router, prefix="/licenses", tags=["licenses"])
api_router.include_router(vulnerability_aging.router, prefix="/vulnerability-aging", tags=["vulnerability-aging"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(impact_simulator.router, prefix="/impact-simulator", tags=["impact-simulator"])
api_router.include_router(remediation.router, prefix="/remediation", tags=["remediation"])
api_router.include_router(live_scan.router, prefix="/live-scan", tags=["live-scan"])
api_router.include_router(seed.router, prefix="", tags=["seed"])
api_router.include_router(risk_prediction.router, prefix="", tags=["risk-prediction"])
api_router.include_router(analyze.router, prefix="", tags=["analyze"])