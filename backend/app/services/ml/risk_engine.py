WEIGHTS = {
    "maintainer_risk": 0.30,
    "security_risk": 0.25,
    "release_health": 0.15,
    "community_health": 0.10,
    "breaking_change_risk": 0.20,
}


def _clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))


def calc_maintainer_risk(f: dict) -> float:
    score = 0
    if f.get("days_since_last_release", 0) > 180:
        score += 30
    elif f.get("days_since_last_release", 0) > 90:
        score += 15
    if f.get("commits_last_6mo", 10) < 5:
        score += 25
    elif f.get("commits_last_6mo", 10) < 20:
        score += 10
    if f.get("maintainer_count", 1) <= 1:
        score += 25
    elif f.get("maintainer_count", 1) <= 2:
        score += 10
    if f.get("pr_merge_time_hours", 48) > 72:
        score += 20
    elif f.get("pr_merge_time_hours", 48) > 24:
        score += 10
    details = []
    if score >= 40:
        details.append("No release in 6+ months" if f.get("days_since_last_release", 0) > 180 else "Infrequent releases")
        details.append("Very few commits recently" if f.get("commits_last_6mo", 10) < 5 else "Low commit activity")
        details.append("Only one active maintainer" if f.get("maintainer_count", 1) <= 1 else "Few maintainers")
        if f.get("pr_merge_time_hours", 0) > 72:
            details.append("Slow PR merge times")
    return _clamp(score), "; ".join(details) if details else "Healthy maintainer activity"


def calc_security_risk(f: dict) -> float:
    score = 0
    cve = f.get("cve_count_3yr", 0)
    if cve >= 5:
        score += 35
    elif cve >= 2:
        score += 20
    elif cve >= 1:
        score += 10
    trend = f.get("cve_trend_slope", 0)
    if trend > 0.5:
        score += 30
    elif trend > 0:
        score += 15
    elif trend < -0.3:
        score -= 10
    if not f.get("has_security_policy"):
        score += 20
    if f.get("is_deprecated"):
        score += 25
    severity_boost = 0
    details = []
    if cve > 0:
        details.append(f"{cve} CVEs in last 3 years")
        if trend > 0:
            details.append("Vulnerability trend increasing")
        if not f.get("has_security_policy"):
            details.append("No security policy")
    score = _clamp(score)
    return score, "; ".join(details) if details else "Clean security record"


def calc_release_health(f: dict) -> float:
    score = 0
    days_since = f.get("days_since_last_release", 180)
    expected_cadence = f.get("release_frequency_days", 90)
    if days_since > expected_cadence * 3:
        score += 40
    elif days_since > expected_cadence * 2:
        score += 25
    elif days_since > expected_cadence:
        score += 10
    details = []
    if days_since > 365:
        details.append("No release in over a year")
    elif days_since > 180:
        details.append(f"No release in {days_since} days")
    details.append(f"Expected release every ~{expected_cadence} days")
    return _clamp(score), "; ".join(details) if details else "On track with release cadence"


def calc_community_health(f: dict) -> float:
    score = 0
    stars = f.get("stars", 0)
    if stars < 100:
        score += 15
    elif stars < 1000:
        score += 5
    downloads = f.get("downloads_monthly", 0)
    download_trend = f.get("download_trend_slope", 0)
    if download_trend < -0.2:
        score += 25
    elif download_trend < -0.05:
        score += 10
    open_issues = f.get("open_issues", 0)
    closure = f.get("issue_closure_rate", 0.7)
    if open_issues > 200:
        score += 10
    if closure < 0.4:
        score += 15
    elif closure < 0.7:
        score += 5
    details = []
    if stars < 100:
        details.append("Few GitHub stars (< 100)")
    if download_trend < -0.2:
        details.append("Downloads declining rapidly")
    elif download_trend < -0.05:
        details.append("Downloads declining")
    if closure < 0.4:
        details.append("Low issue closure rate")
    return _clamp(score), "; ".join(details) if details else "Healthy community engagement"


def calc_breaking_change_risk(f: dict) -> float:
    score = 0
    breaking = f.get("breaking_change_count", 0)
    if breaking >= 5:
        score += 50
    elif breaking >= 3:
        score += 30
    elif breaking >= 1:
        score += 15
    details = []
    if breaking > 0:
        details.append(f"{int(breaking)} major breaking changes")
        details.append("High migration effort for upgrades")
    return _clamp(score), "; ".join(details) if details else "Stable API with few breaking changes"


def compute_all_risks(features: dict) -> dict:
    mr, mr_d = calc_maintainer_risk(features)
    sr, sr_d = calc_security_risk(features)
    rh, rh_d = calc_release_health(features)
    ch, ch_d = calc_community_health(features)
    br, br_d = calc_breaking_change_risk(features)

    combined = (
        mr * WEIGHTS["maintainer_risk"]
        + sr * WEIGHTS["security_risk"]
        + rh * WEIGHTS["release_health"]
        + ch * WEIGHTS["community_health"]
        + br * WEIGHTS["breaking_change_risk"]
    )

    return {
        "overall_risk": round(combined, 1),
        "factors": [
            {"name": "Maintainer Risk", "score": mr, "weight": WEIGHTS["maintainer_risk"], "detail": mr_d},
            {"name": "Security Risk", "score": sr, "weight": WEIGHTS["security_risk"], "detail": sr_d},
            {"name": "Release Health", "score": rh, "weight": WEIGHTS["release_health"], "detail": rh_d},
            {"name": "Community Health", "score": ch, "weight": WEIGHTS["community_health"], "detail": ch_d},
            {"name": "Breaking Change Risk", "score": br, "weight": WEIGHTS["breaking_change_risk"], "detail": br_d},
        ],
        "breakdown": {k: round(v, 1) for k, v in zip(
            ["maintainer_risk", "security_risk", "release_health", "community_health", "breaking_change_risk"],
            [mr, sr, rh, ch, br],
        )},
    }
