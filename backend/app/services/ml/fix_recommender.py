import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import joblib
import os
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class FixOption:
    fix_type: str
    target_version: str
    breaking_change: bool
    migration_effort: str
    migration_guide: Optional[str]
    confidence: float
    reasoning: str
    affected_apis: List[str]
    test_coverage_impact: float


class FixRecommender:
    def __init__(self, db_session=None):
        self.db = db_session
        self.breaking_change_model = None
        self.effort_estimator = None
        self._load_models()
    
    def _load_models(self):
        model_dir = os.path.join(settings.ml_model_path, "fix_recommender")
        bc_path = os.path.join(model_dir, "breaking_change_model.pkl")
        effort_path = os.path.join(model_dir, "effort_estimator.pkl")
        
        if os.path.exists(bc_path):
            try:
                self.breaking_change_model = joblib.load(bc_path)
            except Exception as e:
                logger.warning(f"Failed to load breaking change model: {e}")
        
        if os.path.exists(effort_path):
            try:
                self.effort_estimator = joblib.load(effort_path)
            except Exception as e:
                logger.warning(f"Failed to load effort estimator: {e}")
    
    async def get_recommendations(
        self,
        vulnerability,
        current_version: str,
        ecosystem: str,
        package_name: str,
        dependencies: Optional[List[Dict]] = None,
    ) -> List[FixOption]:
        recommendations = []
        
        fixed_versions = vulnerability.fixed_versions or []
        affected_versions = vulnerability.affected_versions or []
        
        if not fixed_versions:
            return [FixOption(
                fix_type="workaround",
                target_version=current_version,
                breaking_change=False,
                migration_effort="medium",
                migration_guide=None,
                confidence=0.5,
                reasoning="No fixed version available. Consider workaround or isolation.",
                affected_apis=[],
                test_coverage_impact=0.0,
            )]
        
        upgrade_options = self._find_upgrade_paths(
            current_version, fixed_versions, affected_versions
        )
        
        for version in upgrade_options:
            fix = await self._analyze_upgrade(
                vulnerability, current_version, version, ecosystem, package_name, dependencies
            )
            recommendations.append(fix)
        
        alternative = await self._find_alternative_package(
            vulnerability, ecosystem, package_name
        )
        if alternative:
            recommendations.append(alternative)
        
        recommendations.sort(key=lambda x: (-x.confidence, x.migration_effort != "low"))
        
        return recommendations
    
    def _find_upgrade_paths(
        self,
        current: str,
        fixed: List[str],
        affected: List[str],
    ) -> List[str]:
        from packaging import version
        
        try:
            current_ver = version.parse(current)
            valid_fixes = []
            
            for f in fixed:
                try:
                    fix_ver = version.parse(f)
                    if fix_ver > current_ver:
                        valid_fixes.append(f)
                except:
                    continue
            
            valid_fixes.sort(key=lambda v: version.parse(v))
            return valid_fixes[:3]
        except:
            return fixed[:3]
    
    async def _analyze_upgrade(
        self,
        vulnerability,
        current_version: str,
        target_version: str,
        ecosystem: str,
        package_name: str,
        dependencies: Optional[List[Dict]],
    ) -> FixOption:
        breaking = await self._predict_breaking_change(
            package_name, current_version, target_version, ecosystem
        )
        
        effort = self._estimate_migration_effort(
            package_name, current_version, target_version, ecosystem, breaking
        )
        
        guide = self._find_migration_guide(package_name, current_version, target_version, ecosystem)
        
        affected_apis = self._get_affected_apis(package_name, current_version, target_version)
        
        test_impact = self._estimate_test_impact(breaking, affected_apis)
        
        confidence = self._calculate_confidence(
            breaking, effort, guide is not None, len(affected_apis)
        )
        
        reasoning = self._generate_reasoning(
            vulnerability, current_version, target_version, breaking, effort, guide
        )
        
        return FixOption(
            fix_type="upgrade",
            target_version=target_version,
            breaking_change=breaking,
            migration_effort=effort,
            migration_guide=guide,
            confidence=confidence,
            reasoning=reasoning,
            affected_apis=affected_apis,
            test_coverage_impact=test_impact,
        )
    
    async def _predict_breaking_change(
        self,
        package_name: str,
        from_version: str,
        to_version: str,
        ecosystem: str,
    ) -> bool:
        from packaging import version
        
        try:
            from_ver = version.parse(from_version)
            to_ver = version.parse(to_version)
            
            if hasattr(from_ver, 'major') and hasattr(to_ver, 'major'):
                if to_ver.major > from_ver.major:
                    return True
                if to_ver.minor > from_ver.minor and to_ver.major == from_ver.major:
                    return ecosystem in ["npm", "pypi"]
            
            return False
        except:
            return True
    
    def _estimate_migration_effort(
        self,
        package_name: str,
        from_version: str,
        to_version: str,
        ecosystem: str,
        breaking: bool,
    ) -> str:
        if not breaking:
            return "low"
        
        major_jump = self._get_major_version_jump(from_version, to_version)
        
        if major_jump >= 2:
            return "very_high"
        elif major_jump == 1:
            return "high" if ecosystem in ["npm", "pypi"] else "medium"
        else:
            return "medium"
    
    def _get_major_version_jump(self, from_v: str, to_v: str) -> int:
        from packaging import version
        try:
            f = version.parse(from_v)
            t = version.parse(to_v)
            if hasattr(f, 'major') and hasattr(t, 'major'):
                return t.major - f.major
        except:
            pass
        return 1
    
    def _find_migration_guide(
        self,
        package_name: str,
        from_version: str,
        to_version: str,
        ecosystem: str,
    ) -> Optional[str]:
        guides = {
            "npm": f"https://github.com/{package_name}/blob/main/MIGRATION.md",
            "pypi": f"https://github.com/{package_name}/blob/main/CHANGELOG.md",
            "maven": f"https://github.com/{package_name}/blob/main/migration-guide.md",
        }
        
        base = guides.get(ecosystem, "")
        if base:
            return f"{base}#v{from_version}-to-v{to_version}"
        return None
    
    def _get_affected_apis(
        self,
        package_name: str,
        from_version: str,
        to_version: str,
    ) -> List[str]:
        return [
            f"API changes between {from_version} and {to_version}",
            "Check changelog for detailed breaking changes",
        ]
    
    def _estimate_test_impact(self, breaking: bool, affected_apis: List[str]) -> float:
        if not breaking:
            return 0.1
        return min(0.8, 0.3 + len(affected_apis) * 0.1)
    
    def _calculate_confidence(
        self,
        breaking: bool,
        effort: str,
        has_guide: bool,
        api_count: int,
    ) -> float:
        confidence = 0.7
        
        if not breaking:
            confidence += 0.15
        if has_guide:
            confidence += 0.1
        if effort == "low":
            confidence += 0.1
        elif effort == "very_high":
            confidence -= 0.15
        
        return max(0.3, min(0.95, confidence))
    
    def _generate_reasoning(
        self,
        vulnerability,
        current: str,
        target: str,
        breaking: bool,
        effort: str,
        guide: Optional[str],
    ) -> str:
        parts = [
            f"Upgrade from {current} to {target} fixes {vulnerability.cve_id or 'vulnerability'}."
        ]
        
        if breaking:
            parts.append(f"This is a breaking change ({effort} migration effort).")
        else:
            parts.append("This is a non-breaking patch upgrade.")
        
        if guide:
            parts.append(f"Migration guide available: {guide}")
        else:
            parts.append("No official migration guide found. Review changelog carefully.")
        
        if vulnerability.cvss_score and vulnerability.cvss_score >= 9.0:
            parts.append("CRITICAL: This vulnerability has a CVSS score >= 9.0. Prioritize immediate upgrade.")
        
        return " ".join(parts)
    
    async def _find_alternative_package(
        self,
        vulnerability,
        ecosystem: str,
        package_name: str,
    ) -> Optional[FixOption]:
        alternatives = {
            "npm": {
                "moment": "date-fns",
                "request": "axios",
                "lodash": "es-toolkit",
                "colors": "chalk",
                "debug": "debug",
            },
            "pypi": {
                "pyyaml": "ruamel.yaml",
                "requests": "httpx",
                "urllib3": "httpx",
            },
            "maven": {},
        }
        
        alt_map = alternatives.get(ecosystem, {})
        alternative = alt_map.get(package_name.lower())
        
        if alternative:
            return FixOption(
                fix_type="replace",
                target_version=alternative,
                breaking_change=True,
                migration_effort="high",
                migration_guide=f"https://github.com/{alternative}/blob/main/MIGRATION.md",
                confidence=0.6,
                reasoning=f"Consider migrating to {alternative} which is actively maintained and not affected by this vulnerability class.",
                affected_apis=["Full API replacement required"],
                test_coverage_impact=0.8,
            )
        
        return None
    
    def _get_ecosystem_migration_effort(self, ecosystem: str) -> Dict[str, str]:
        return {
            "npm": {"patch": "low", "minor": "medium", "major": "high"},
            "pypi": {"patch": "low", "minor": "low", "major": "medium"},
            "maven": {"patch": "low", "minor": "low", "major": "medium"},
            "go": {"patch": "low", "minor": "low", "major": "low"},
        }.get(ecosystem, {"patch": "low", "minor": "medium", "major": "high"})