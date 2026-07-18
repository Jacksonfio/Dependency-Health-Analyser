import httpx
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class OSVCollector:
    def __init__(self):
        self.base_url = "https://api.osv.dev/v1"
    
    async def query_vulnerabilities(self, ecosystem: str, package_name: str) -> List[Dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/query",
                    json={
                        "package": {"name": package_name, "ecosystem": ecosystem.upper()},
                        "version": None,
                    }
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = []
                    for vuln in data.get("vulns", []):
                        results.append(self._parse_osv_vuln(vuln))
                    return results
                return []
        except Exception as e:
            logger.warning(f"Failed to query OSV for {ecosystem}/{package_name}: {e}")
            return []
    
    async def query_recent_vulnerabilities(self, ecosystem: str, days: int = 7) -> List[Dict[str, Any]]:
        return []
    
    def _parse_osv_vuln(self, vuln: Dict) -> Dict[str, Any]:
        cve_id = None
        for alias in vuln.get("aliases", []):
            if alias.startswith("CVE-"):
                cve_id = alias
                break
        
        affected = vuln.get("affected", [{}])[0] if vuln.get("affected") else {}
        package_info = affected.get("package", {})
        ecosystem = package_info.get("ecosystem", "").lower()
        package_name = package_info.get("name", "")
        
        ranges = affected.get("ranges", [{}])[0] if affected.get("ranges") else {}
        events = ranges.get("events", [])
        affected_versions = [e.get("introduced", "0") for e in events if "introduced" in e] or ["0"]
        fixed_versions = [e.get("fixed") for e in events if "fixed" in e] or None
        
        summary = vuln.get("summary") or vuln.get("details", "")[:200]
        
        severity = "MEDIUM"
        database_specific = vuln.get("database_specific", {})
        severity_parts = database_specific.get("severity", "")
        severity_map = {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
        if isinstance(severity_parts, str):
            severity = severity_map.get(severity_parts.upper(), "MEDIUM")
        
        return {
            "cve_id": cve_id,
            "osv_id": vuln.get("id"),
            "ghsa_id": next((a for a in vuln.get("aliases", []) if a.startswith("GHSA-")), None),
            "ecosystem": ecosystem or "npm",
            "package_name": package_name,
            "affected_versions": affected_versions,
            "fixed_versions": fixed_versions,
            "summary": summary,
            "details": vuln.get("details"),
            "severity": severity,
            "cvss_score": database_specific.get("cvss_score"),
            "cvss_vector": database_specific.get("cvss_vector"),
            "cwe_ids": vuln.get("database_specific", {}).get("cwe_ids", []),
            "references": [{"url": r.get("url")} for r in vuln.get("references", [])],
            "published_at": vuln.get("published"),
            "modified_at": vuln.get("modified"),
        }