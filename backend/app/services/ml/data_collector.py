import httpx
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


async def collect_package_features(name: str, ecosystem: str, github_token: str = "") -> dict:
    features = {
        "days_since_last_release": 180,
        "commits_last_6mo": 10,
        "maintainer_count": 1,
        "open_issues": 50,
        "closed_issues": 100,
        "pr_merge_time_hours": 48,
        "cve_count_3yr": 2,
        "cve_trend_slope": 0.0,
        "release_frequency_days": 180,
        "breaking_change_count": 1,
        "downloads_monthly": 50000,
        "download_trend_slope": -0.05,
        "stars": 1000,
        "forks": 200,
        "contributors": 5,
        "issue_closure_rate": 0.7,
        "has_security_policy": 0,
        "is_deprecated": 0,
    }

    if ecosystem == "npm":
        await _enrich_from_npm(name, features, github_token)
    elif ecosystem == "pypi":
        await _enrich_from_pypi(name, features)

    await _enrich_from_osv(name, ecosystem.upper(), features)

    repo_url = features.get("_repo_url", "")
    if repo_url and "github.com" in repo_url:
        await _enrich_from_github(repo_url, features, github_token)

    for k in list(features.keys()):
        if k.startswith("_"):
            del features[k]

    return features


async def _enrich_from_npm(name: str, features: dict, token: str = ""):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://registry.npmjs.org/{name}")
            if r.status_code != 200:
                return
            data = r.json()
            if data.get("deprecated"):
                features["is_deprecated"] = 1
            features["maintainer_count"] = len(data.get("maintainers", []))
            features["_repo_url"] = ""
            repo = data.get("repository", {})
            if isinstance(repo, dict):
                features["_repo_url"] = (repo.get("url") or "").replace("git+", "").replace(".git", "")
            elif isinstance(repo, str):
                features["_repo_url"] = repo.replace("git+", "").replace(".git", "")

            times = data.get("time", {})
            versions = [v for v in times.keys() if v not in ("created", "modified")]
            if versions:
                last_ver = max(versions, key=lambda v: times.get(v, ""))
                last_date = times.get(last_ver, "")
                if last_date:
                    try:
                        dt = datetime.fromisoformat(last_date.replace("Z", "+00:00"))
                        features["days_since_last_release"] = (datetime.now(timezone.utc) - dt).days
                    except:
                        pass
                if len(versions) > 1:
                    dates = []
                    for v in versions[-10:]:
                        try:
                            dates.append(datetime.fromisoformat(times[v].replace("Z", "+00:00")))
                        except:
                            pass
                    if len(dates) >= 2:
                        intervals = [(dates[i] - dates[i + 1]).days for i in range(len(dates) - 1)]
                        features["release_frequency_days"] = max(1, abs(sum(intervals) // len(intervals)))

            downloads_url = f"https://api.npmjs.org/downloads/point/last-month/{name}"
            dr = await c.get(downloads_url)
            if dr.status_code == 200:
                features["downloads_monthly"] = dr.json().get("downloads", 50000)

    except Exception as e:
        logger.warning(f"npm fetch error for {name}: {e}")


async def _enrich_from_pypi(name: str, features: dict):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"https://pypi.org/pypi/{name}/json")
            if r.status_code != 200:
                return
            data = r.json()
            info = data.get("info", {})
            features["maintainer_count"] = 1
            urls = info.get("project_urls", {})
            features["_repo_url"] = urls.get("Repository", urls.get("Source", ""))

            releases = data.get("releases", {})
            dates = []
            for ver, files in releases.items():
                if files:
                    try:
                        d = datetime.fromisoformat(files[0].get("upload_time_iso_8601", "").replace("Z", "+00:00"))
                        dates.append((ver, d))
                    except:
                        pass
            dates.sort(key=lambda x: x[1])
            if dates:
                last = dates[-1][1]
                features["days_since_last_release"] = (datetime.now(timezone.utc) - last).days
                if len(dates) > 1:
                    intervals = [(dates[i][1] - dates[i - 1][1]).days for i in range(1, len(dates))]
                    features["release_frequency_days"] = max(1, abs(sum(intervals) // len(intervals)))

    except Exception as e:
        logger.warning(f"pypi fetch error for {name}: {e}")


async def _enrich_from_osv(name: str, ecosystem: str, features: dict):
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post("https://api.osv.dev/v1/query", json={"package": {"name": name, "ecosystem": ecosystem}, "version": None})
            if r.status_code != 200:
                return
            data = r.json()
            vulns = data.get("vulns", [])
            years = {}
            severities = []
            for v in vulns:
                published = v.get("published", "")
                if published:
                    try:
                        year = datetime.fromisoformat(published.replace("Z", "+00:00")).year
                        years[year] = years.get(year, 0) + 1
                    except:
                        pass
                sev = "MEDIUM"
                ds = v.get("database_specific", {})
                if isinstance(ds, dict):
                    sev = (ds.get("severity") or "MEDIUM").upper()
                severities.append(sev)

            features["cve_count_3yr"] = len(vulns)

            sorted_years = sorted(years.keys())
            if len(sorted_years) >= 2:
                counts = [years[y] for y in sorted_years]
                if len(counts) >= 2:
                    features["cve_trend_slope"] = (counts[-1] - counts[0]) / max(len(counts), 1)

    except Exception as e:
        logger.warning(f"OSV fetch error for {name}: {e}")


async def _enrich_from_github(repo_url: str, features: dict, token: str = ""):
    try:
        parts = repo_url.rstrip("/").split("/")
        if len(parts) < 2:
            return
        owner, repo = parts[-2], parts[-1]
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        async with httpx.AsyncClient(timeout=15, headers=headers) as c:
            rr = await c.get(f"https://api.github.com/repos/{owner}/{repo}")
            if rr.status_code != 200:
                return
            gh = rr.json()
            features["stars"] = gh.get("stargazers_count", 1000)
            features["forks"] = gh.get("forks_count", 200)
            features["open_issues"] = gh.get("open_issues_count", 50)
            features["has_security_policy"] = 1 if gh.get("security_and_analysis", {}).get("secret_scanning", {}).get("status") == "enabled" else 0

            cr = await c.get(f"https://api.github.com/repos/{owner}/{repo}/contributors?per_page=5&anon=false")
            if cr.status_code == 200:
                features["contributors"] = len(cr.json())

            com = await c.get(f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=5&since={(datetime.now(timezone.utc).isoformat())}")
            if com.status_code == 200:
                features["commits_last_6mo"] = len(com.json())

    except Exception as e:
        logger.warning(f"github fetch error for {repo_url}: {e}")
