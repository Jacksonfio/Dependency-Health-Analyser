'use client';

import { useState, useEffect, useCallback } from 'react';
import { Menu, Search, AlertTriangle, TrendingUp, Shield, Users, GitBranch, Activity, ArrowUp, ArrowDown, Minus, ExternalLink } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import api from '@/lib/api';

const RISK_LABELS: Record<string, { label: string; color: string; icon: any }> = {
  maintainer_risk: { label: 'Maintainer', color: '#f97316', icon: Users },
  security_risk: { label: 'Security', color: '#ef4444', icon: Shield },
  release_health: { label: 'Release Health', color: '#eab308', icon: Activity },
  community_health: { label: 'Community', color: '#3b82f6', icon: TrendingUp },
  breaking_change_risk: { label: 'Breaking Changes', color: '#a855f7', icon: GitBranch },
};

function getRiskColor(score: number) {
  if (score >= 70) return '#ef4444';
  if (score >= 50) return '#f97316';
  if (score >= 30) return '#eab308';
  return '#22c55e';
}

function getRiskLabel(score: number) {
  if (score >= 70) return 'Critical';
  if (score >= 50) return 'High';
  if (score >= 30) return 'Medium';
  return 'Low';
}

function RiskGauge({ score, size = 120 }: { score: number; size?: number }) {
  const radius = size / 2 - 10;
  const circ = 2 * Math.PI * radius;
  const offset = circ - (score / 100) * circ;
  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#1a1a1a" strokeWidth="6" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={radius} stroke={getRiskColor(score)} strokeWidth="6" fill="none"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-white">{score}</span>
        <span className="text-[8px] text-gray-500 mt-0.5">/ 100</span>
      </div>
    </div>
  );
}

export default function RiskPredictionPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [packages, setPackages] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [selectedPkg, setSelectedPkg] = useState<any | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/v1/packages/search', { params: { q: '', limit: 50 } });
        setPackages(res.data.items || res.data || []);
      } catch {}
    })();
  }, []);

  const analyze = useCallback(async (pkg: any) => {
    setSelectedPkg(pkg);
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/api/v1/risk-prediction/package/${pkg.id}`);
      setResult(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to analyze package');
    }
    setLoading(false);
  }, []);

  const filtered = packages.filter((p: any) =>
    p.name?.toLowerCase().includes(search.toLowerCase())
  );

  const riskChange = result ? (result.ml_prediction?.projected_risk_90d - result.combined_score) : 0;

  return (
    <div className="min-h-screen bg-surface">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:ml-56">
        <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-lg border-b border-border bg-gradient-header">
          <div className="flex items-center justify-between h-12 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded-lg hover:bg-stone-800/40 text-stone-400"><Menu className="h-4 w-4" /></button>
              <h1 className="font-semibold text-white text-sm">Risk Prediction</h1>
            </div>
          </div>
        </header>
        <main className="px-4 sm:px-6 pb-4 sm:pb-6 pt-2 space-y-2">
          <p className="text-[10px] text-gray-500">AI-powered dependency risk analysis with future projection</p>

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
            <input
              type="text" placeholder="Search packages in your projects..." value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-card border border-[#222222] rounded-lg pl-9 pr-3 py-2 text-xs text-white placeholder-gray-600 focus:outline-none focus:border-[#444] transition-colors"
            />
            {search && filtered.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-[#222222] rounded-lg shadow-xl z-20 max-h-48 overflow-y-auto">
                {filtered.map((p: any) => (
                  <button key={p.id} onClick={() => { setSearch(''); analyze(p); }}
                    className="w-full text-left px-3 py-2 text-xs text-gray-300 hover:bg-stone-800/40 transition-colors border-b border-border last:border-0">
                    <span className="font-medium text-white">{p.name}</span>
                    <span className="text-gray-600 ml-2">{p.ecosystem || 'npm'}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-800/30 rounded-lg">
              <AlertTriangle className="h-3.5 w-3.5 text-red-400 flex-shrink-0" />
              <p className="text-xs text-red-300">{error}</p>
            </div>
          )}

          {loading && (
            <div className="card rounded-lg p-12 animate-pulse flex items-center justify-center">
              <div className="flex flex-col items-center gap-2">
                <Activity className="h-5 w-5 text-gray-600 animate-spin" />
                <p className="text-xs text-gray-500">Analyzing {selectedPkg?.name}...</p>
              </div>
            </div>
          )}

          {result && !loading && (
            <>
              {/* Header Stats */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Current Risk</p>
                  <p className="text-lg font-bold mt-0.5" style={{ color: getRiskColor(result.combined_score) }}>
                    {result.combined_score}/100
                  </p>
                  <p className="text-[8px] text-gray-600">{getRiskLabel(result.combined_score)}</p>
                </div>
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Projected (90d)</p>
                  <p className="text-lg font-bold mt-0.5" style={{ color: getRiskColor(result.ml_prediction?.projected_risk_90d) }}>
                    {result.ml_prediction?.projected_risk_90d}/100
                  </p>
                  <p className="text-[8px] text-gray-600">{getRiskLabel(result.ml_prediction?.projected_risk_90d)}</p>
                </div>
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Risk Change</p>
                  <div className="flex items-center gap-1 mt-0.5">
                    {riskChange > 5 ? <ArrowUp className="h-4 w-4 text-red-400" /> : riskChange < -5 ? <ArrowDown className="h-4 w-4 text-green-400" /> : <Minus className="h-4 w-4 text-gray-500" />}
                    <p className="text-lg font-bold" style={{ color: riskChange > 0 ? '#ef4444' : riskChange < 0 ? '#22c55e' : '#9ca3af' }}>
                      {riskChange > 0 ? '+' : ''}{riskChange.toFixed(1)}
                    </p>
                  </div>
                  <p className="text-[8px] text-gray-600">Over 90 days</p>
                </div>
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Package</p>
                  <p className="text-sm font-medium text-white mt-0.5 truncate">{result.package?.name}</p>
                  <p className="text-[8px] text-gray-600">{result.package?.ecosystem}</p>
                </div>
              </div>

              {/* Main Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-2">
                {/* Risk Factors */}
                <div className="lg:col-span-2 card rounded-lg p-4">
                  <h2 className="text-xs font-medium text-white mb-3">Risk Factor Breakdown</h2>
                  <div className="space-y-2.5">
                    {result.risk_factors?.map((f: any) => {
                      const meta = RISK_LABELS[f.name.toLowerCase().replace(/\s+/g, '_')] || { label: f.name, color: '#6b7280', icon: Activity };
                      const Icon = meta.icon;
                      return (
                        <div key={f.name} className="bg-card rounded-lg p-2.5">
                          <div className="flex items-center justify-between mb-1.5">
                            <div className="flex items-center gap-2">
                              <Icon className="h-3 w-3" style={{ color: meta.color }} />
                              <span className="text-xs text-gray-300">{meta.label}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500">{(f.weight * 100).toFixed(0)}%</span>
                              <span className="text-sm font-bold" style={{ color: getRiskColor(f.score) }}>{f.score}</span>
                            </div>
                          </div>
                          <div className="h-1.5 bg-stone-800/40 rounded-full overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-500" style={{ width: `${f.score}%`, backgroundColor: meta.color }} />
                          </div>
                          {f.detail && <p className="text-[9px] text-gray-600 mt-1">{f.detail}</p>}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Explanation & Recommendation */}
                <div className="space-y-2">
                  <div className="card rounded-lg p-4">
                    <h2 className="text-xs font-medium text-white mb-3">Assessment</h2>
                    <div className="flex items-center justify-center mb-3">
                      <RiskGauge score={result.combined_score} />
                    </div>
                    <div className="text-center">
                      <span className={`inline-block px-2 py-0.5 rounded text-[9px] font-medium`}
                        style={{ backgroundColor: getRiskColor(result.combined_score) + '20', color: getRiskColor(result.combined_score) }}>
                        {result.explanation?.risk_level?.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <div className="card rounded-lg p-4">
                    <h2 className="text-xs font-medium text-white mb-2">Key Drivers</h2>
                    <ul className="space-y-1">
                      {result.explanation?.key_factors?.map((f: string, i: number) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <AlertTriangle className="h-3 w-3 text-orange-400 mt-0.5 flex-shrink-0" />
                          <span className="text-[10px] text-gray-400">{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="card rounded-lg p-4">
                    <h2 className="text-xs font-medium text-white mb-2">Warnings</h2>
                    <ul className="space-y-1">
                      {result.explanation?.warning?.map((w: string, i: number) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <AlertTriangle className="h-3 w-3 text-red-400 mt-0.5 flex-shrink-0" />
                          <span className="text-[10px] text-gray-400">{w}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="card rounded-lg p-4">
                    <h2 className="text-xs font-medium text-white mb-2">Recommendations</h2>
                    <ul className="space-y-1">
                      {result.explanation?.recommendations?.map((r: string, i: number) => (
                        <li key={i} className="flex items-start gap-1.5">
                          <ArrowUp className="h-3 w-3 text-green-400 mt-0.5 flex-shrink-0" />
                          <span className="text-[10px] text-gray-400">{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* Feature Importance */}
              <div className="card rounded-lg p-4">
                <h2 className="text-xs font-medium text-white mb-3">Feature Importance</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-600 text-[9px] uppercase border-b border-border">
                        <th className="text-left py-1.5 px-1">Feature</th>
                        <th className="text-right py-1.5 px-1">Value</th>
                        <th className="text-right py-1.5 px-1">Impact</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.feature_importance?.slice(0, 10).map((fi: any) => (
                        <tr key={fi.feature} className="border-b border-border/50">
                          <td className="py-1.5 px-1 text-gray-300">{fi.feature.replace(/_/g, ' ')}</td>
                          <td className="py-1.5 px-1 text-right text-gray-500">{typeof fi.value === 'number' ? fi.value.toFixed(1) : fi.value}</td>
                          <td className="py-1.5 px-1 text-right">
                            <span className={`font-medium ${fi.importance > 0 ? 'text-red-400' : 'text-green-400'}`}>
                              {fi.importance > 0 ? '+' : ''}{fi.importance.toFixed(1)}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {!selectedPkg && !loading && (
            <div className="border border-dashed border-stone-700/50 rounded-lg p-12 flex flex-col items-center justify-center bg-gradient-card">
              <Activity className="h-8 w-8 text-gray-700 mb-2" />
              <p className="text-xs text-gray-600">Select a package above to analyze its risk profile</p>
              <p className="text-[9px] text-gray-700 mt-1">Data sourced from npm, PyPI, OSV, and GitHub</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
