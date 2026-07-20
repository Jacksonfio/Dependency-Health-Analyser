# DepHealth - Predictive Dependency Health Monitoring

> Stop reacting to vulnerabilities. Start predicting them

DepHealth is a predictive dependency health platform that forecasts future risk trajectories for your software dependencies. Unlike traditional scanners that only tell you about current vulnerabilities, DepHealth predicts which dependencies will become problematic in the next 90 days and provides prioritized upgrade roadmaps.

## 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **Future Risk Score** | Predicts dependency health 90 days out using ML models |
| **Maintainer Health Analysis** | Tracks commit frequency, PR response times, bus factor, abandonment signals |
| **CVE Velocity Prediction** | Forecasts vulnerability discovery rates based on historical patterns |
| **Ecosystem Migration Detection** | Identifies community shifts (e.g., Moment.js → Day.js) |
| **Upgrade Roadmap** | Prioritized, time-boxed upgrade plans with effort estimates |
| **Automated PR Generation** | Creates upgrade PRs with breaking change analysis |
| **CI/CD Integration** | GitHub Actions, GitLab CI, Jenkins, Azure DevOps |

## 🏗 Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Collectors │────▶│  Feature Store  │────▶│  ML Pipeline    │
│  (GitHub, NVD,   │     │  (PostgreSQL +  │     │  (XGBoost,      │
│   OSV, Registries)│     │   Neo4j)        │     │   Prophet, GNN) │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                         │
┌─────────────────┐     ┌─────────────────┐             │
│  Frontend       │◀───│  API Gateway    │◀────────────┘
│  (Next.js +     │     │  (FastAPI)      │
│   Recharts)     │     └─────────────────┘
└─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- GitHub Personal Access Token (for API access)
- NVD API Key (optional, for enhanced CVE data)
- OpenAI API Key (optional, for AI recommendations)

### Development Setup

```bash
# Clone and start
git clone https://github.com/yourusername/dep-health.git
cd dep-health

# Copy environment files
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Start all services
./start-dev.sh
```

### Access Points
| Service | URL |
|---------|-----|
| Frontend Dashboard | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 |
| Celery Monitor (Flower) | http://localhost:5555 |

## 📊 Dashboard Overview

The dashboard provides:

1. **Risk Timeline Chart** - Visualizes projected risk over 90 days with confidence intervals
2. **Upgrade Roadmap** - Four-tier priority system (Immediate, 2 Weeks, 1 Month, 3 Months)
3. **Project Health Cards** - Per-project scores with vulnerability breakdowns
4. **Real-time Alerts** - New vulnerabilities, deprecations, migration signals

## 🔬 ML Models

### Maintenance Health Model
- **Features**: Release frequency, maintainer activity, issue/PR response times, bus factor, governance files
- **Algorithm**: Random Forest Regressor
- **Output**: 0-100 maintenance score

### Security Risk Model
- **Features**: CVE velocity, severity distribution, exploit availability, fix availability, vendor response time
- **Algorithm**: Gradient Boosting Regressor
- **Output**: 0-100 risk score

### Community Health Model
- **Features**: Download trends, dependent count, GitHub stars/forks, migration indicators
- **Algorithm**: Random Forest Regressor
- **Output**: 0-100 community score

### Exploit Predictor
- **Features**: CVSS vector, CWE category, days since publication, patch availability, PoC existence
- **Algorithm**: Gradient Boosting Classifier
- **Output**: Exploit probability, time-to-exploit estimate, maturity level

### Fix Recommender
- Analyzes version diffs, breaking changes, migration guides
- Outputs upgrade/replace/workaround recommendations with confidence scores

## 📦 Supported Ecosystems

- ✅ npm (JavaScript/TypeScript)
- ✅ PyPI (Python)
- ✅ Maven Central (Java/Kotlin)
- ✅ Docker Hub (Containers)
- 🔄 Go, NuGet, Cargo, Pub, Composer, CocoaPods (planned)

## 🔧 Configuration

Key environment variables:

```bash
# Required
GITHUB_TOKEN=ghp_xxx              # GitHub API access
DATABASE_URL=postgresql+asyncpg://...

# Optional (enhanced features)
NVD_API_KEY=xxx                   # NVD CVE database
OPENAI_API_KEY=sk-xxx             # AI explanations
NEO4J_PASSWORD=xxx                # Graph database
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest --cov=app --cov-report=html

# Frontend tests
cd frontend
npm test -- --coverage
```

## 📈 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/packages/search` | Search packages |
| `GET /api/v1/packages/{id}/health` | Get package health score |
| `GET /api/v1/vulnerabilities/search` | Search vulnerabilities |
| `POST /api/v1/projects` | Create project |
| `GET /api/v1/projects/{id}/health` | Project health report |
| `GET /api/v1/projects/{id}/risk-timeline` | 90-day risk projection |
| `GET /api/v1/projects/{id}/upgrade-plan` | Prioritized upgrade roadmap |
| `POST /api/v1/projects/{id}/scan` | Trigger dependency scan |

## 🚢 Deployment

### Docker Compose (Production)
```bash
docker-compose -f infra/docker/docker-compose.prod.yml up -d
```

### Kubernetes
```bash
kubectl apply -f infra/k8s/
```

### Environment-Specific Configs
- `infra/docker/docker-compose.dev.yml` - Development
- `infra/docker/docker-compose.prod.yml` - Production
- `infra/k8s/` - Kubernetes manifests with HPA

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a PR

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- GitHub API for repository data
- NVD/OSV for vulnerability data
- Libraries.io for dependency graphs
- Open source ML libraries (scikit-learn, XGBoost, Prophet)

---

**Built with ❤️ for developers who want to sleep better at night.**
