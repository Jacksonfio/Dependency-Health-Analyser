from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import UserSetting
from app.services.analyzer.github_repo import analyze_github_repo, parse_dependency_file
from app.services.analyzer.batch_analyzer import batch_analyze
from sqlalchemy import select
import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analyze", tags=["analyze"])


async def _get_github_token(db: AsyncSession) -> str:
    sq = select(UserSetting).where(UserSetting.key == "github_token", UserSetting.section == "api_keys")
    sr = await db.execute(sq)
    st = sr.scalar_one_or_none()
    if st:
        try:
            v = json.loads(st.value)
            return v.get("value", "")
        except:
            pass
    return ""


@router.post("/github")
async def analyze_github(url: str = Form(...), db: AsyncSession = Depends(get_db)):
    github_token = await _get_github_token(db)
    try:
        repo_info = await analyze_github_repo(url, github_token)
    except ValueError as e:
        raise HTTPException(400, str(e))

    if not repo_info["dependencies"]:
        raise HTTPException(400, "No supported dependency files found in repository")

    analysis = await batch_analyze(repo_info["dependencies"], github_token)

    return {
        "repo": repo_info["repo"],
        "url": repo_info["url"],
        "files_found": repo_info["files_found"],
        "dependencies_found": repo_info["dependencies"],
        "analysis": analysis,
    }


@router.post("/upload")
async def analyze_upload(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    content = await file.read()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(400, "File must be UTF-8 encoded text")

    filename = file.filename.lower()
    if filename.endswith(".json"):
        # Try package.json
        try:
            jd = json.loads(text)
            if "dependencies" in jd or "devDependencies" in jd:
                ecosystem = "npm"
            else:
                ecosystem = "npm"
        except:
            raise HTTPException(400, "Invalid JSON file")
    elif filename.endswith(".txt") or filename.endswith(".in"):
        ecosystem = "pypi"
    elif filename.endswith(".xml"):
        if "<project" in text and "xmlns" in text:
            ecosystem = "maven"
        else:
            raise HTTPException(400, "Unsupported XML format")
    else:
        ecosystem = "npm"

    if filename == "pipfile" or filename == "pipfile.lock":
        ecosystem = "pypi"

    deps = parse_dependency_file(text, ecosystem, filename)
    if not deps:
        raise HTTPException(400, "No dependencies found in file")

    github_token = await _get_github_token(db)
    analysis = await batch_analyze(deps, github_token)

    return {
        "filename": file.filename,
        "ecosystem": ecosystem,
        "dependencies_found": deps,
        "analysis": analysis,
    }
