import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class NPMCollector:
    def __init__(self):
        self.base_url = "https://registry.npmjs.org"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_package(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            resp = await self.client.get(f"{self.base_url}/{name}")
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            return self._parse_package(name, data)
        except Exception as e:
            logger.warning(f"Failed to fetch npm package {name}: {e}")
            return None
    
    def _parse_package(self, name: str, data: Dict) -> Dict[str, Any]:
        versions = data.get("versions", {})
        dist_tags = data.get("dist-tags", {})
        latest_version = dist_tags.get("latest")
        
        version_list = []
        for version, v_data in versions.items():
            version_list.append({
                "version": version,
                "published_at": self._parse_date(v_data.get("time", {}).get(version)),
                "is_latest": version == latest_version,
                "is_deprecated": bool(v_data.get("deprecated")),
                "deprecation_reason": v_data.get("deprecated"),
                "downloads": None,
                "size_bytes": v_data.get("dist", {}).get("unpackedSize"),
            })
        
        version_list.sort(key=lambda v: v["published_at"] or "", reverse=True)
        
        return {
            "ecosystem": "npm",
            "name": name,
            "description": data.get("description"),
            "homepage": data.get("homepage"),
            "repository_url": self._extract_repo_url(data),
            "license": data.get("license"),
            "keywords": data.get("keywords", []),
            "downloads_last_month": None,
            "dependents_count": None,
            "maintainers": data.get("maintainers", []),
            "versions": version_list,
        }
    
    def _extract_repo_url(self, data: Dict) -> Optional[str]:
        repo = data.get("repository")
        if isinstance(repo, dict):
            return repo.get("url", "").replace("git+", "").replace(".git", "")
        elif isinstance(repo, str):
            return repo.replace("git+", "").replace(".git", "")
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except:
            return None
    
    async def close(self):
        await self.client.aclose()


class PyPICollector:
    def __init__(self):
        self.base_url = "https://pypi.org/pypi"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_package(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            resp = await self.client.get(f"{self.base_url}/{name}/json")
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            return self._parse_package(name, data)
        except Exception as e:
            logger.warning(f"Failed to fetch PyPI package {name}: {e}")
            return None
    
    def _parse_package(self, name: str, data: Dict) -> Dict[str, Any]:
        info = data.get("info", {})
        releases = data.get("releases", {})
        
        version_list = []
        for version, files in releases.items():
            if not files:
                continue
            file_info = files[0]
            version_list.append({
                "version": version,
                "published_at": self._parse_date(file_info.get("upload_time_iso_8601") or file_info.get("upload_time")),
                "is_latest": version == info.get("version"),
                "is_deprecated": False,
                "deprecation_reason": None,
                "downloads": None,
                "size_bytes": file_info.get("size"),
            })
        
        version_list.sort(key=lambda v: v["published_at"] or "", reverse=True)
        
        return {
            "ecosystem": "pypi",
            "name": name,
            "description": info.get("summary"),
            "homepage": info.get("home_page"),
            "repository_url": self._extract_repo_url(info),
            "license": info.get("license"),
            "keywords": info.get("keywords", "").split(", ") if info.get("keywords") else [],
            "downloads_last_month": None,
            "dependents_count": None,
            "maintainers": [],
            "versions": version_list,
        }
    
    def _extract_repo_url(self, info: Dict) -> Optional[str]:
        urls = [
            info.get("project_urls", {}).get("Repository"),
            info.get("project_urls", {}).get("Source"),
            info.get("project_urls", {}).get("Homepage"),
        ]
        for url in urls:
            if url and "github.com" in url:
                return url
        return None
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except:
            return None
    
    async def close(self):
        await self.client.aclose()


class MavenCollector:
    def __init__(self):
        self.base_url = "https://search.maven.org/solrsearch/select"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_package(self, group_id: str, artifact_id: str) -> Optional[Dict[str, Any]]:
        try:
            query = f'g:"{group_id}" AND a:"{artifact_id}"'
            params = {"q": query, "rows": 20, "wt": "json"}
            
            resp = await self.client.get(self.base_url, params=params)
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            docs = data.get("response", {}).get("docs", [])
            if not docs:
                return None
            
            return self._parse_package(group_id, artifact_id, docs)
        except Exception as e:
            logger.warning(f"Failed to fetch Maven package {group_id}:{artifact_id}: {e}")
            return None
    
    def _parse_package(self, group_id: str, artifact_id: str, docs: List[Dict]) -> Dict[str, Any]:
        latest = max(docs, key=lambda d: d.get("timestamp", 0))
        
        versions = []
        for doc in docs:
            versions.append({
                "version": doc.get("v", ""),
                "published_at": self._parse_timestamp(doc.get("timestamp")),
                "is_latest": doc.get("v") == latest.get("v"),
                "is_deprecated": False,
                "deprecation_reason": None,
                "downloads": None,
                "size_bytes": None,
            })
        
        versions.sort(key=lambda v: v["published_at"] or "", reverse=True)
        
        name = f"{group_id}:{artifact_id}"
        
        return {
            "ecosystem": "maven",
            "name": name,
            "description": latest.get("description"),
            "homepage": latest.get("url"),
            "repository_url": latest.get("scm"),
            "license": latest.get("license"),
            "keywords": [],
            "downloads_last_month": None,
            "dependents_count": None,
            "maintainers": [],
            "versions": versions,
        }
    
    def _parse_timestamp(self, ts: Optional[int]) -> Optional[str]:
        if not ts:
            return None
        try:
            from datetime import datetime
            return datetime.fromtimestamp(ts / 1000).isoformat()
        except:
            return None
    
    async def close(self):
        await self.client.aclose()


class DockerCollector:
    def __init__(self):
        self.base_url = "https://hub.docker.com/v2"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def fetch_package(self, name: str) -> Optional[Dict[str, Any]]:
        try:
            if "/" not in name:
                name = f"library/{name}"
            
            resp = await self.client.get(f"{self.base_url}/repositories/{name}/tags", params={"page_size": 100})
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            return self._parse_package(name, data)
        except Exception as e:
            logger.warning(f"Failed to fetch Docker image {name}: {e}")
            return None
    
    def _parse_package(self, name: str, data: Dict) -> Dict[str, Any]:
        results = data.get("results", [])
        
        versions = []
        for tag in results:
            if tag.get("name") == "latest":
                continue
            versions.append({
                "version": tag.get("name", ""),
                "published_at": self._parse_date(tag.get("last_updated")),
                "is_latest": tag.get("name") == "latest",
                "is_deprecated": False,
                "deprecation_reason": None,
                "downloads": tag.get("full_size"),
                "size_bytes": tag.get("full_size"),
            })
        
        versions.sort(key=lambda v: v["published_at"] or "", reverse=True)
        
        if versions:
            versions[0]["is_latest"] = True
        
        return {
            "ecosystem": "docker",
            "name": name,
            "description": None,
            "homepage": f"https://hub.docker.com/r/{name}",
            "repository_url": None,
            "license": None,
            "keywords": [],
            "downloads_last_month": None,
            "dependents_count": None,
            "maintainers": [],
            "versions": versions,
        }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        try:
            from datetime import datetime
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).isoformat()
        except:
            return None
    
    async def close(self):
        await self.client.aclose()