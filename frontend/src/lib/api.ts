import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

export default api;

export const packagesApi = {
  search: (params: { q: string; ecosystem?: string; limit?: number; offset?: number }) =>
    api.get('/api/v1/packages/search', { params }),
  get: (id: string, params?: { include_versions?: boolean; include_vulns?: boolean; include_health?: boolean }) =>
    api.get(`/api/v1/packages/${id}`, { params }),
  getVersions: (id: string, limit?: number) =>
    api.get(`/api/v1/packages/${id}/versions`, { params: { limit } }),
  getVulnerabilities: (id: string, params?: { severity?: string; fixed_only?: boolean }) =>
    api.get(`/api/v1/packages/${id}/vulnerabilities`, { params }),
  getHealth: (id: string) =>
    api.get(`/api/v1/packages/${id}/health`),
  getDependents: (id: string, limit?: number) =>
    api.get(`/api/v1/packages/${id}/dependents`, { params: { limit } }),
  getDependencyGraph: (id: string, params?: { depth?: number; direction?: string }) =>
    api.get(`/api/v1/packages/${id}/dependency-graph`, { params }),
  getPopular: (ecosystem: string, limit?: number) =>
    api.get(`/api/v1/packages/ecosystem/${ecosystem}/popular`, { params: { limit } }),
  refresh: (id: string) =>
    api.post(`/api/v1/packages/${id}/refresh`),
};

export const vulnerabilitiesApi = {
  search: (params: {
    q?: string;
    cve_id?: string;
    ecosystem?: string;
    package_name?: string;
    severity?: string;
    min_cvss?: number;
    max_cvss?: number;
    published_after?: string;
    published_before?: string;
    has_fix?: boolean;
    limit?: number;
    offset?: number;
  }) => api.get('/api/v1/vulnerabilities/search', { params }),
  get: (id: string, params?: { include_exploit_prediction?: boolean; include_fix_recommendation?: boolean }) =>
    api.get(`/api/v1/vulnerabilities/${id}`, { params }),
  getExploitPrediction: (id: string) =>
    api.get(`/api/v1/vulnerabilities/${id}/exploit-prediction`),
  getFixRecommendations: (id: string) =>
    api.get(`/api/v1/vulnerabilities/${id}/fix-recommendations`),
  getAffectedPackages: (id: string, limit?: number) =>
    api.get(`/api/v1/vulnerabilities/${id}/affected-packages`, { params: { limit } }),
  getTrending: (params?: { ecosystem?: string; days?: number; limit?: number }) =>
    api.get('/api/v1/vulnerabilities/trending', { params }),
  getStats: (ecosystem?: string) =>
    api.get('/api/v1/vulnerabilities/stats/summary', { params: { ecosystem } }),
};

export const projectsApi = {
  create: (data: any) =>
    api.post('/api/v1/projects', data),
  list: (params?: { ecosystem?: string; is_monitored?: boolean; owner_id?: string; organization_id?: string; search?: string; limit?: number; offset?: number }) =>
    api.get('/api/v1/projects', { params }),
  get: (id: string, params?: { include_dependencies?: boolean; include_scans?: boolean; include_health?: boolean }) =>
    api.get(`/api/v1/projects/${id}`, { params }),
  update: (id: string, data: any) =>
    api.patch(`/api/v1/projects/${id}`, data),
  delete: (id: string) =>
    api.delete(`/api/v1/projects/${id}`),
  triggerScan: (id: string, scanType?: string) =>
    api.post(`/api/v1/projects/${id}/scan`, { scan_type: scanType }),
  getScans: (id: string, params?: { limit?: number; offset?: number }) =>
    api.get(`/api/v1/projects/${id}/scans`, { params }),
  getLatestScan: (id: string) =>
    api.get(`/api/v1/projects/${id}/scans/latest`),
  getDependencies: (id: string, params?: { include_vulns?: boolean; include_health?: boolean; direct_only?: boolean }) =>
    api.get(`/api/v1/projects/${id}/dependencies`, { params }),
  getHealth: (id: string) =>
    api.get(`/api/v1/projects/${id}/health`),
  getHealthHistory: (id: string, params?: { days?: number; limit?: number }) =>
    api.get(`/api/v1/projects/${id}/health/history`, { params }),
  refresh: (id: string) =>
    api.post(`/api/v1/projects/${id}/refresh`),
  getUpgradePlan: (id: string, params?: { max_effort?: string }) =>
    api.get(`/api/v1/projects/${id}/upgrade-plan`, { params }),
  getRiskTimeline: (id: string, params?: { days?: number }) =>
    api.get(`/api/v1/projects/${id}/risk-timeline`, { params }),
};

export const dashboardApi = {
  getStats: () =>
    api.get('/api/v1/dashboard/stats'),
  getAlerts: (params?: { limit?: number }) =>
    api.get('/api/v1/dashboard/alerts', { params }),
};

export const settingsApi = {
  get: (section: string) =>
    api.get(`/api/v1/settings/${section}`),
  updateSection: (section: string, data: Record<string, any>) =>
    api.put(`/api/v1/settings/${section}`, data),
  updateKey: (section: string, key: string, value: any) =>
    api.put(`/api/v1/settings/${section}/${key}`, { value }),
};

export const analyzeApi = {
  github: (url: string) => {
    const form = new FormData();
    form.append('url', url);
    return api.post('/api/v1/analyze/github', form);
  },
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/api/v1/analyze/upload', form);
  },
};

export const riskPredictionApi = {
  byPackage: (packageId: string) =>
    api.get(`/api/v1/risk-prediction/package/${packageId}`),
  byName: (ecosystem: string, packageName: string) =>
    api.get(`/api/v1/risk-prediction/by-name/${ecosystem}/${packageName}`),
};

export const healthApi = {
  getPackageHealth: (packageId: string) =>
    api.get(`/api/v1/health/packages/${packageId}`),
  getProjectHealth: (projectId: string) =>
    api.get(`/api/v1/health/projects/${projectId}`),
  getHealthHistory: (projectId: string, params?: { days?: number; limit?: number }) =>
    api.get(`/api/v1/health/projects/${projectId}/history`, { params }),
};