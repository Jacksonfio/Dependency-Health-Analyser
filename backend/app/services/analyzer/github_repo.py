import httpx
import re
import logging

logger = logging.getLogger(__name__)

DEPENDENCY_FILES = {
    "package.json": "npm",
    "requirements.txt": "pypi",
    "requirements.in": "pypi",
    "Pipfile": "pypi",
    "poetry.lock": "pypi",
    "pom.xml": "maven",
    "build.gradle": "maven",
    "Cargo.toml": "cargo",
    "go.mod": "go",
}

async def get_repo_default_branch(owner: str, repo: str, token: str = "") -> list:
    branches = ["main", "master"]
    if token:
        headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {token}"}
        async with httpx.AsyncClient(timeout=15, headers=headers) as c:
            r = await c.get(f"https://api.github.com/repos/{owner}/{repo}")
            if r.status_code == 200:
                branch = r.json().get("default_branch", "main")
                return [branch]
    return branches


async def list_repo_files(owner: str, repo: str, branches: list, token: str = "") -> list:
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    files_found = []

    async with httpx.AsyncClient(timeout=30, headers=headers) as c:
        for branch in branches:
            tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            r = await c.get(tree_url)
            if r.status_code == 200:
                tree = r.json().get("tree", [])
                for entry in tree:
                    path = entry.get("path", "")
                    for dep_file, eco in DEPENDENCY_FILES.items():
                        if path.endswith(dep_file):
                            files_found.append({"path": path, "ecosystem": eco})
                            break
                if files_found:
                    return files_found

        # Fallback: try known root-level dependency files via raw content
        root_files = ["package.json", "requirements.txt", "requirements.in", "Pipfile", "pom.xml", "build.gradle"]
        for branch in branches:
            for filename in root_files:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
                tr = await c.get(raw_url)
                if tr.status_code == 200:
                    eco = DEPENDENCY_FILES.get(filename, "npm")
                    files_found.append({"path": filename, "ecosystem": eco})
            if files_found:
                return files_found

    return files_found


async def fetch_file_content(owner: str, repo: str, path: str, branches: list, token: str = "") -> str:
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
        # Try raw.githubusercontent.com first (no rate limit issues) with each branch
        for b in branches:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{b}/{path}"
            r = await c.get(raw_url)
            if r.status_code == 200:
                return r.text

    # Fallback to GitHub API with token
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    async with httpx.AsyncClient(timeout=15, headers=headers) as c:
        for b in branches:
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={b}"
            r = await c.get(url)
            if r.status_code == 200:
                data = r.json()
                import base64
                return base64.b64decode(data.get("content", "")).decode("utf-8")

    raise ValueError(f"Cannot fetch {path} in any branch: {branches}")


async def analyze_github_repo(url: str, github_token: str = "") -> dict:
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/.*)?$", url.rstrip("/"))
    if not match:
        raise ValueError(f"Invalid GitHub URL: {url}")
    owner, repo = match.group(1), match.group(2)
    repo = repo.replace(".git", "")

    branches = await get_repo_default_branch(owner, repo, github_token)
    files = await list_repo_files(owner, repo, branches, github_token)

    dependencies = []
    for f in files:
        try:
            content = await fetch_file_content(owner, repo, f["path"], branches, github_token)
            deps = parse_dependency_file(content, f["ecosystem"], f["path"])
            dependencies.extend(deps)
        except Exception as e:
            logger.warning(f"Failed to parse {f['path']}: {e}")

    return {
        "repo": f"{owner}/{repo}",
        "url": url,
        "branch": branches[0],
        "files_found": files,
        "dependencies": dependencies,
    }


def parse_dependency_file(content: str, ecosystem: str, filename: str) -> list:
    if filename == "package.json" or filename.endswith("package.json"):
        return _parse_package_json(content, ecosystem)
    elif filename == "requirements.txt" or filename == "requirements.in":
        return _parse_requirements_txt(content, ecosystem)
    elif filename == "Pipfile":
        return _parse_pipfile(content)
    elif filename == "pom.xml":
        return _parse_pom_xml(content)
    else:
        logger.warning(f"No parser for {filename}")
        return []


def _parse_package_json(content: str, ecosystem: str) -> list:
    deps = []
    try:
        import json
        data = json.loads(content)
        for section in ("dependencies", "devDependencies", "peerDependencies"):
            for name, version in data.get(section, {}).items():
                deps.append({
                    "name": name,
                    "version": version.strip("^~>=<"),
                    "version_spec": version,
                    "ecosystem": ecosystem,
                    "dependency_type": "dev" if section == "devDependencies" else "runtime",
                })
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse package.json: {e}")
    return deps


def _parse_requirements_txt(content: str, ecosystem: str) -> list:
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"^([a-zA-Z0-9_.-]+)\s*([><=!~]+\s*[\w.*-]+)?", line)
        if match:
            name = match.group(1)
            version = match.group(2) or ""
            deps.append({
                "name": name,
                "version": version.strip(">=<~! "),
                "version_spec": version.strip() if version else "",
                "ecosystem": ecosystem,
                "dependency_type": "runtime",
            })
    return deps


def _parse_pipfile(content: str) -> list:
    deps = []
    current_section = None
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].lower()
            continue
        if "=" in line and current_section in ("packages", "dev-packages"):
            name = line.split("=")[0].strip().strip('"').strip("'")
            version = line.split("=")[1].strip().strip('"').strip("'")
            deps.append({
                "name": name,
                "version": version.replace("*", "").strip("=\"'"),
                "version_spec": version,
                "ecosystem": "pypi",
                "dependency_type": "dev" if current_section == "dev-packages" else "runtime",
            })
    return deps


def _parse_pom_xml(content: str) -> list:
    deps = []
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(content)
        ns = {"": "http://maven.apache.org/POM/4.0.0"}
        for dep in root.findall(".//dependency", ns):
            group = dep.findtext("groupId", "", ns)
            artifact = dep.findtext("artifactId", "", ns)
            version = dep.findtext("version", "", ns)
            if group and artifact:
                full_name = f"{group}:{artifact}"
                deps.append({
                    "name": full_name,
                    "version": version,
                    "version_spec": version,
                    "ecosystem": "maven",
                    "dependency_type": "runtime",
                })
    except ET.ParseError as e:
        logger.warning(f"Failed to parse pom.xml: {e}")
    return deps
