'use client';

import { useState, useEffect } from 'react';
import { Menu, Shield, Wrench, Play, CheckCircle, XCircle, Clock, AlertTriangle, Loader2, Filter, Zap } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import api from '@/lib/api';

const statusColor: Record<string, string> = { open: 'text-red-400 bg-red-500/10 border-red-500/30', in_progress: 'text-blue-400 bg-blue-500/10 border-blue-500/30', scheduled: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30', resolved: 'text-green-400 bg-green-500/10 border-green-500/30' };
const severityColor: Record<string, string> = { CRITICAL: 'text-red-400', HIGH: 'text-orange-400', MEDIUM: 'text-yellow-400', LOW: 'text-green-400' };

export default function RemediationPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [data, setData] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [autoFixRunning, setAutoFixRunning] = useState(false);
  const [autoFixResult, setAutoFixResult] = useState<any>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const load = () => {
    setLoading(true);
    const params: any = {};
    if (statusFilter) params.status = statusFilter;
    api.get('/api/v1/remediation/pipeline', { params })
      .then(r => setData(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
    api.get('/api/v1/remediation/stats').then(r => setStats(r.data)).catch(() => {});
  };

  useEffect(() => { load(); }, [statusFilter]);

  const runAutoFix = async () => {
    setAutoFixRunning(true);
    setAutoFixResult(null);
    try {
      const r = await api.post('/api/v1/remediation/auto-fix');
      setAutoFixResult(r.data);
      load();
    } catch { setAutoFixResult(null); }
    setAutoFixRunning(false);
  };

  const applyFix = async (id: string) => {
    try {
      await api.post(`/api/v1/remediation/apply/${id}`);
      load();
    } catch {}
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:ml-56">
        <header className="sticky top-0 z-40 bg-[#0a0a0a]/80 backdrop-blur-lg border-b border-[#1a1a1a]">
          <div className="flex items-center justify-between h-12 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded-lg hover:bg-[#1a1a1a] text-gray-400"><Menu className="h-4 w-4" /></button>
              <h1 className="font-semibold text-white text-sm">Auto-Remediation Pipeline</h1>
            </div>
          </div>
        </header>
        <main className="px-4 sm:px-6 pb-4 sm:pb-6 pt-2 space-y-3 max-w-4xl">
          <p className="text-[10px] text-gray-500">Automated dependency fix pipeline — detect, prioritize, and fix issues across projects</p>

          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Fixes This Week</p><p className="text-lg font-semibold text-white">{stats.fixes_this_week}</p></div>
              <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Avg Resolution</p><p className="text-lg font-semibold text-orange-400">{stats.avg_resolution_time_hours}h</p></div>
              <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Auto-Fix Rate</p><p className="text-lg font-semibold text-green-400">{stats.auto_fix_success_rate}%</p></div>
              <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Open Issues</p><p className="text-lg font-semibold text-red-400">{data?.summary?.open || 0}</p></div>
            </div>
          )}

          <div className="flex items-center gap-2">
            <button onClick={runAutoFix} disabled={autoFixRunning}
              className="flex items-center gap-1.5 px-4 py-2 bg-green-700 hover:bg-green-800 disabled:opacity-50 text-xs text-white rounded-lg transition-colors"
            >
              {autoFixRunning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Zap className="h-3.5 w-3.5" />}
              Run Auto-Fix
            </button>
            <div className="flex items-center gap-1 ml-auto">
              <Filter className="h-3 w-3 text-gray-600" />
              <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="bg-[#111] border border-[#2a2a2a] rounded text-[10px] text-gray-400 px-2 py-1.5 outline-none focus:border-gray-500">
                <option value="">All Status</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="scheduled">Scheduled</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          </div>

          {autoFixResult && (
            <div className="border border-green-500/30 bg-green-500/10 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <CheckCircle className="h-4 w-4 text-green-400" />
                <p className="text-xs text-green-400">{autoFixResult.summary}</p>
              </div>
              <div className="flex gap-3 mt-2 text-[10px] text-gray-500">
                <span>{autoFixResult.fixes_applied} fixes applied</span>
                <span>{autoFixResult.vulnerabilities_mitigated} vulns mitigated</span>
                <span>{autoFixResult.duration_seconds}s</span>
              </div>
            </div>
          )}

          {loading ? (
            <p className="text-[10px] text-gray-500 text-center py-6">Loading...</p>
          ) : data?.items?.length > 0 ? (
            <div className="border border-[#1a1a1a] rounded-lg overflow-hidden">
              {data.summary && (
                <div className="px-3 py-2 bg-[#111] border-b border-[#1a1a1a] flex gap-4 text-[10px]">
                  <span>Total: <strong className="text-white">{data.summary.total}</strong></span>
                  <span className="text-red-400">Open: {data.summary.open}</span>
                  <span className="text-blue-400">In Progress: {data.summary.in_progress}</span>
                  <span className="text-green-400">Resolved: {data.summary.resolved}</span>
                </div>
              )}
              <div className="divide-y divide-[#1a1a1a]">
                {data.items.map((item: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-2.5 hover:bg-[#111] transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-300">{item.package_name}</span>
                        <span className="text-[9px] text-gray-600">{item.current_version} → {item.target_version}</span>
                        <span className={`text-[9px] ${severityColor[item.severity] || 'text-gray-500'}`}>{item.severity}</span>
                      </div>
                      <p className="text-[9px] text-gray-600 mt-0.5">{item.project_name} · {item.issue_type} · {item.effort} effort</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded border ${statusColor[item.status] || 'text-gray-500 border-gray-700'}`}>{item.status.replace('_', ' ')}</span>
                      {item.status === 'open' && (
                        <button onClick={() => applyFix(item.id)} className="p-1 rounded hover:bg-[#1a1a1a] text-gray-500 hover:text-blue-400 transition-colors">
                          <Play className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[10px] text-gray-600 text-center py-6">No remediation items found</p>
          )}
        </main>
      </div>
    </div>
  );
}
