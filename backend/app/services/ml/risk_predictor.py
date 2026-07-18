import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os
from pathlib import Path

MODEL_DIR = Path(__file__).parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

FEATURE_NAMES = [
    "days_since_last_release",
    "commits_last_6mo",
    "maintainer_count",
    "open_issues",
    "closed_issues",
    "pr_merge_time_hours",
    "cve_count_3yr",
    "cve_trend_slope",
    "release_frequency_days",
    "breaking_change_count",
    "downloads_monthly",
    "download_trend_slope",
    "stars",
    "forks",
    "contributors",
    "issue_closure_rate",
    "has_security_policy",
    "is_deprecated",
]


def _generate_synthetic_training_data(n_samples=500):
    np.random.seed(42)
    X = np.zeros((n_samples, len(FEATURE_NAMES)))
    for i in range(n_samples):
        X[i, 0] = np.random.uniform(0, 730)  # days since last release
        X[i, 1] = np.random.exponential(20)  # commits last 6mo
        X[i, 2] = max(1, int(np.random.exponential(3)))  # maintainers
        X[i, 3] = np.random.exponential(100)  # open issues
        X[i, 4] = np.random.exponential(200)  # closed issues
        X[i, 5] = np.random.uniform(1, 168)  # PR merge time hours
        X[i, 6] = np.random.poisson(3)  # CVE count 3yr
        X[i, 7] = np.random.uniform(-2, 3)  # CVE trend slope
        X[i, 8] = np.random.uniform(30, 365)  # release frequency days
        X[i, 9] = np.random.poisson(2)  # breaking changes
        X[i, 10] = np.random.exponential(500000)  # downloads monthly
        X[i, 11] = np.random.uniform(-0.5, 0.3)  # download trend
        X[i, 12] = np.random.exponential(5000)  # stars
        X[i, 13] = np.random.exponential(500)  # forks
        X[i, 14] = max(1, int(np.random.exponential(10)))  # contributors
        X[i, 15] = np.random.uniform(0.3, 0.95)  # issue closure rate
        X[i, 16] = np.random.choice([0, 1], p=[0.6, 0.4])  # security policy
        X[i, 17] = np.random.choice([0, 1], p=[0.9, 0.1])  # deprecated
    y = (
        0.3 * np.clip(X[:, 0] / 365, 0, 1)  # old release = risky
        + 0.2 * (1 - np.clip(X[:, 1] / 50, 0, 1))  # few commits = risky
        + 0.15 * (1 - np.clip(X[:, 2] / 5, 0, 1))  # few maintainers = risky
        + 0.25 * np.clip(X[:, 6] / 10, 0, 1)  # many CVEs = risky
        + 0.2 * np.clip(X[:, 7], 0, 1)  # increasing CVE trend = risky
        + 0.15 * np.clip((X[:, 8] - 90) / 270, 0, 1)  # slow releases = risky
        + 0.1 * np.clip(X[:, 9] / 5, 0, 1)  # many breaking changes = risky
        - 0.1 * np.clip(X[:, 11], -1, 0)  # declining downloads = risky
        + 0.1 * (1 - X[:, 15])  # low closure rate = risky
        + 0.15 * (1 - X[:, 16])  # no security policy = risky
        + 0.2 * X[:, 17]  # deprecated = risky
        + np.random.normal(0, 0.08, n_samples)
    )
    y = np.clip(y * 100, 0, 100)
    return X, y


def get_model():
    model_path = MODEL_DIR / "risk_predictor.joblib"
    scaler_path = MODEL_DIR / "scaler.joblib"

    if model_path.exists() and scaler_path.exists():
        model = joblib.load(str(model_path))
        scaler = joblib.load(str(scaler_path))
        return model, scaler

    X, y = _generate_synthetic_training_data(500)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=1)
    model.fit(X_scaled, y)
    joblib.dump(model, str(model_path))
    joblib.dump(scaler, str(scaler_path))
    return model, scaler


def predict_risk(features: dict) -> dict:
    model, scaler = get_model()
    X = np.array([[features.get(f, 0) for f in FEATURE_NAMES]])
    X_scaled = scaler.transform(X)
    current_score = float(model.predict(X_scaled)[0])

    future_features = features.copy()
    future_features["days_since_last_release"] += 90
    future_features["cve_count_3yr"] = features.get("cve_count_3yr", 0) + max(0, features.get("cve_trend_slope", 0) * 3)
    future_features["commits_last_6mo"] = max(0, features.get("commits_last_6mo", 0) - 2)
    future_features["downloads_monthly"] = max(0, features.get("downloads_monthly", 0) * (1 + features.get("download_trend_slope", 0) * 3))
    X_future = np.array([[future_features.get(f, 0) for f in FEATURE_NAMES]])
    X_future_scaled = scaler.transform(X_future)
    future_score = float(model.predict(X_future_scaled)[0])

    return {
        "current_risk": round(current_score, 1),
        "projected_risk_90d": round(future_score, 1),
        "risk_change": round(future_score - current_score, 1),
    }


def get_feature_importance(features: dict) -> list:
    _, scaler = get_model()
    model_path = MODEL_DIR / "risk_predictor.joblib"
    model = joblib.load(str(model_path))

    X = np.array([[features.get(f, 0) for f in FEATURE_NAMES]])
    X_scaled = scaler.transform(X)
    pred = model.predict(X_scaled)[0]

    importances = []
    for i, name in enumerate(FEATURE_NAMES):
        X_perturb = X_scaled.copy()
        X_perturb[0, i] = 0
        pred_perturb = model.predict(X_perturb)[0]
        impact = pred - pred_perturb
        importances.append({"feature": name, "value": features.get(name, 0), "importance": round(float(impact), 2)})

    importances.sort(key=lambda x: abs(x["importance"]), reverse=True)
    return importances
