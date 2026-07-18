import httpx
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GitHubCollector:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DepHealth/1.0",
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
    
    async def get_repository_data(self, repo_url: str) -> Dict[str, Any]:
        try:
            owner, repo = self._parse_repo_url(repo_url)
            if not owner or not repo:
                return {}
            
            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
                repo_data = await self._fetch_repo(client, owner, repo)
                if not repo_data:
                    return {}
                
                contributors = await self._fetch_contributors(client, owner, repo)
                commit_activity = await self._fetch_commit_activity(client, owner, repo)
                issues_data = await self._fetch_issues(client, owner, repo)
                pr_data = await self._fetch_pull_requests(client, owner, repo)
                
                return self._process_repo_data(
                    repo_data, contributors, commit_activity, issues_data, pr_data
                )
        except Exception as e:
            logger.warning(f"Failed to fetch GitHub data for {repo_url}: {e}")
            return {}
    
    def _parse_repo_url(self, url: str) -> tuple:
        import re
        patterns = [
            r"github\.com[:/]([^/]+)/([^/.]+)",
            r"github\.com/([^/]+)/([^/.]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1), match.group(2).replace(".git", "")
        return None, None
    
    async def _fetch_repo(self, client: httpx.AsyncClient, owner: str, repo: str) -> Optional[Dict]:
        resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}")
        if resp.status_code == 200:
            return resp.json()
        return None
    
    async def _fetch_contributors(self, client: httpx.AsyncClient, owner: str, repo: str) -> list:
        resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/contributors", params={"per_page": 100})
        if resp.status_code == 200:
            return resp.json()
        return []
    
    async def _fetch_commit_activity(self, client: httpx.AsyncClient, owner: str, repo: str) -> list:
        resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/stats/commit_activity")
        if resp.status_code == 200:
            return resp.json()
        return []
    
    async def _fetch_issues(self, client: httpx.AsyncClient, owner: str, repo: str) -> Dict[str, Any]:
        open_resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/issues", params={"state": "open", "per_page": 100})
        closed_resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/issues", params={"state": "closed", "per_page": 100})
        
        open_issues = open_resp.json() if open_resp.status_code == 200 else []
        closed_issues = closed_resp.json() if closed_resp.status_code == 200 else []
        
        return {"open": open_issues, "closed": closed_issues}
    
    async def _fetch_pull_requests(self, client: httpx.AsyncClient, owner: str, repo: str) -> list:
        resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/pulls", params={"state": "all", "per_page": 100})
        if resp.status_code == 200:
            return resp.json()
        return []
    
    def _process_repo_data(self, repo_data: Dict, contributors: list, commit_activity: list, issues: Dict, prs: list) -> Dict[str, Any]:
        now = datetime.utcnow()
        
        active_maintainers = len([c for c in contributors if c.get("contributions", 0) > 5])
        total_contributors = len(contributors)
        
        commits_per_week = 0
        if commit_activity:
            recent_weeks = commit_activity[-4:] if len(commit_activity) >= 4 else commit_activity
            commits_per_week = sum(week.get("total", 0) for week in recent_weeks) / max(1, len(recent_weeks))
        
        bus_factor = min(active_maintainers, 5)
        
        open_issues = [i for i in issues.get("open", []) if "pull_request" not in i]
        closed_issues = [i for i in issues.get("closed", []) if "pull_request" not in i]
        
        issue_response_times = []
        for issue in closed_issues[:50]:
            created = issue.get("created_at")
            closed = issue.get("closed_at")
            if created and closed:
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    closed_dt = datetime.fromisoformat(closed.replace("Z", "+00:00"))
                    hours = (closed_dt - created_dt).total_seconds() / 3600
                    issue_response_times.append(hours)
                except:
                    pass
        
        avg_issue_response = sum(issue_response_times) / len(issue_response_times) if issue_response_times else 720
        
        pr_merge_times = []
        for pr in prs[:50]:
            if pr.get("merged_at") and pr.get("created_at"):
                try:
                    created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                    merged = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                    hours = (merged - created).total_seconds() / 3600
                    pr_merge_times.append(hours)
                except:
                    pass
        
        avg_pr_merge = sum(pr_merge_times) / len(pr_merge_times) if pr_merge_times else 168
        
        open_count = len(open_issues)
        closed_count = len(closed_issues)
        total_issues = open_count + closed_count
        issues_trend = 0
        if total_issues > 0:
            issues_trend = (open_count - closed_count) / total_issues
        
        has_security_policy = bool(repo_data.get("security_policy_url") or repo_data.get("has_security_policy"))
        has_code_of_conduct = bool(repo_data.get("code_of_conduct"))
        has_contributing = bool(repo_data.get("has_contributing"))
        
        release_notes_quality = 0.5
        if repo_data.get("releases_url"):
            release_notes_quality = 0.7
        
        dep_update_freq = 0
        
        return {
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "watchers": repo_data.get("watchers_count", 0),
            "contributors": total_contributors,
            "active_maintainers": max(1, active_maintainers),
            "commits_per_week": round(commits_per_week, 1),
            "bus_factor": bus_factor,
            "open_issues": open_count,
            "closed_issues": closed_count,
            "issues_trend": round(issues_trend, 2),
            "avg_issue_response_hours": round(avg_issue_response, 1),
            "avg_pr_merge_hours": round(avg_pr_merge, 1),
            "has_security_policy": has_security_policy,
            "has_code_of_conduct": has_code_of_conduct,
            "has_contributing": has_contributing,
            "release_notes_quality": release_notes_quality,
            "dep_update_freq": dep_update_freq,
            "is_archived": repo_data.get("archived", False),
            "default_branch": repo_data.get("default_branch", "main"),
        }