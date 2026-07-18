from typing import Optional, List, Dict
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import UserSetting
from pydantic import BaseModel

router = APIRouter()

class SettingValue(BaseModel):
    value: dict

class SettingResponse(BaseModel):
    id: str
    section: str
    key: str
    value: dict
    updated_at: str

    model_config = {"from_attributes": True}

class SettingsSectionResponse(BaseModel):
    section: str
    settings: list[SettingResponse]

DEFAULT_SETTINGS: dict[str, dict[str, dict]] = {
    "notifications": {
        "email_alerts": {"enabled": True, "email": ""},
        "slack_webhook": {"enabled": False, "url": ""},
        "alert_types": {"new_vulns": True, "scan_complete": True, "fix_available": False, "expired_certs": True},
    },
    "api-keys": {
        "github": {"token": "", "username": ""},
        "nvd": {"api_key": ""},
        "openai": {"api_key": ""},
    },
    "integrations": {
        "cicd": {"jenkins_url": "", "github_actions": False, "gitlab_ci": False},
        "webhooks": {"url": "", "events": ["scan_complete", "new_vulnerability"]},
        "sso": {"enabled": False, "provider": "", "client_id": "", "client_secret": ""},
    },
    "team": {},
    "security": {
        "two_factor": {"enabled": False, "method": "app"},
        "session": {"timeout_minutes": 60, "max_sessions": 5},
        "audit_log": {"enabled": True, "retention_days": 90},
    },
}

@router.get("/{section}")
async def get_settings(
    section: str,
    user_id: UUID = Query("00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db),
):
    if section not in DEFAULT_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Section '{section}' not found")

    query = select(UserSetting).where(
        UserSetting.user_id == user_id,
        UserSetting.section == section,
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    existing = {r.key: r for r in rows}
    settings = {}
    for key, default_val in DEFAULT_SETTINGS[section].items():
        if key in existing:
            settings[key] = existing[key].value
        else:
            settings[key] = default_val

    return {"section": section, "settings": settings}

@router.put("/{section}/{key}")
async def upsert_setting(
    section: str,
    key: str,
    body: SettingValue,
    user_id: UUID = Query("00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db),
):
    if section not in DEFAULT_SETTINGS or key not in DEFAULT_SETTINGS[section]:
        raise HTTPException(status_code=404, detail=f"Setting '{section}/{key}' not found")

    query = select(UserSetting).where(
        UserSetting.user_id == user_id,
        UserSetting.section == section,
        UserSetting.key == key,
    )
    result = await db.execute(query)
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = body.value
    else:
        from app.db.models import uuid
        setting = UserSetting(
            id=uuid.uuid4(),
            user_id=user_id,
            section=section,
            key=key,
            value=body.value,
        )
        db.add(setting)

    await db.commit()
    await db.refresh(setting)
    return {"section": section, "key": key, "value": setting.value}

@router.put("/{section}")
async def update_section(
    section: str,
    body: dict,
    user_id: UUID = Query("00000000-0000-0000-0000-000000000001"),
    db: AsyncSession = Depends(get_db),
):
    if section not in DEFAULT_SETTINGS:
        raise HTTPException(status_code=404, detail=f"Section '{section}' not found")

    from app.db.models import uuid as uuid_mod

    for key, value in body.items():
        if key not in DEFAULT_SETTINGS[section]:
            continue
        query = select(UserSetting).where(
            UserSetting.user_id == user_id,
            UserSetting.section == section,
            UserSetting.key == key,
        )
        result = await db.execute(query)
        setting = result.scalar_one_or_none()
        if setting:
            setting.value = value
        else:
            setting = UserSetting(
                id=uuid_mod.uuid4(),
                user_id=user_id,
                section=section,
                key=key,
                value=value,
            )
            db.add(setting)

    await db.commit()
    return {"section": section, "status": "saved"}
