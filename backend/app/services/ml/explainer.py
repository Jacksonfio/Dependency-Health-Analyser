def generate_explanation(features: dict, risk_result: dict, ml_result: dict) -> dict:
    factors = risk_result["factors"]
    reasons = []
    warnings = []
    recommendations = []

    for f in factors:
        if f["score"] >= 50:
            reasons.append(f["name"])
            warnings.append(f["detail"])

    if not warnings:
        warnings.append("All risk factors within acceptable range")

    future_change = ml_result.get("risk_change", 0)
    if future_change > 10:
        recommendations.append("Upgrade within 30 days — risk projected to increase significantly")
    elif future_change > 5:
        recommendations.append("Plan upgrade within 60 days — risk trending upward")
    else:
        recommendations.append("Risk is stable — continue monitoring monthly")

    if features.get("is_deprecated"):
        recommendations.insert(0, "CRITICAL: This package is deprecated — migrate immediately")

    if features.get("cve_trend_slope", 0) > 0.5:
        recommendations.append("CVE trend is worsening — prioritize security audit")

    if features.get("days_since_last_release", 0) > 365:
        if recommendations:
            recommendations.insert(1, "Last release was over a year ago — consider an active fork or alternative")
        else:
            recommendations.append("Look for actively maintained alternatives")

    return {
        "risk_level": _risk_level(risk_result["overall_risk"]),
        "score": risk_result["overall_risk"],
        "future_score": ml_result.get("projected_risk_90d", risk_result["overall_risk"]),
        "key_factors": reasons[:3],
        "warning": warnings[:3],
        "recommendations": recommendations[:3],
    }


def _risk_level(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 30:
        return "medium"
    return "low"
