from app.services.collectors.github_collector import GitHubCollector
from app.services.collectors.registry_collectors import NPMCollector, PyPICollector, MavenCollector, DockerCollector
from app.db.models import Ecosystem


DEFAULT_COLLECTORS = {
    Ecosystem.NPM: NPMCollector(),
    Ecosystem.MAVEN: MavenCollector(),
    Ecosystem.PYPI: PyPICollector(),
    Ecosystem.DOCKER: DockerCollector(),
}

GITHUB_COLLECTOR = GitHubCollector()


def get_collector(ecosystem: Ecosystem):
    return DEFAULT_COLLECTORS.get(ecosystem)


def get_github_collector():
    return GITHUB_COLLECTOR