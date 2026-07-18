'use client';

import { useState, useEffect } from 'react';
import { Menu, Shield, GitBranch, Play, ArrowUpDown, AlertTriangle, Scale, Activity, Loader2, Check, X, ArrowUp, ArrowDown } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import api from '@/lib/api';

export default function ImpactSimulatorPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [scenarios, setScenarios] = useState<any[]>([]);
  const [selected, setSelected] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/api/v1/impact-simulator/scenarios').then(r => setScenarios(r.data.scenarios || [])).catch(() => {});
  }, []);

  const simulate = async () => {
    if (!selected) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await api.post(`/api/v1/impact-simulator/simulate?scenario_id=${selected}`);
      setResult(r.data);
    } catch { setResult(null); }
    setLoading(false);
  };

  const deltaColor = (val: number, invert = false) => {
    if (val === 0) return 'text-gray-500';
    const good = invert ? val < 0 : val > 0;
    return good ? 'text-green-400' : 'text-red-400';
  };

  const DeltaIcon = ({ val, invert = false }: { val: number; invert?: boolean }) => {
    if (val === 0) return null;
    const good = invert ? val < 0 : val > 0;
    return good ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />;
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:ml-56">
        <header className="sticky top-0 z-40 bg-[#0a0a0a]/80 backdrop-blur-lg border-b border-[#1a1a1a]">
          <div className="flex items-center justify-between h-12 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded-lg hover:bg-[#1a1a1a] text-gray-400"><Menu className="h-4 w-4" /></button>
              <h1 className="font-semibold text-white text-sm">Dependency Impact Simulator</h1>
            </div>
          </div>
        </header>
        <main className="px-4 sm:px-6 pb-4 sm:pb-6 pt-2 space-y-3 max-w-4xl">
          <p className="text-[10px] text-gray-500">Simulate dependency changes and see the predicted impact before making real changes</p>

          <div className="border border-[#1a1a1a] rounded-lg p-3">
            <h2 className="text-xs font-medium text-white mb-2">Choose a Scenario</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
              {scenarios.map((s: any, i: number) => (
                <button key={i} onClick={() => setSelected(s.id)}
                  className={`text-left p-2.5 rounded-lg border text-xs transition-colors ${
                    selected === s.id
                      ? 'border-blue-500/50 bg-blue-500/10 text-white'
                      : 'border-[#1a1a1a] bg-[#111] text-gray-400 hover:border-[#333] hover:text-gray-300'
                  }`}
                >
                  <p className="font-medium">{s.name}</p>
                  <p className="text-[9px] text-gray-600 mt-0.5">{s.description}</p>
                </button>
              ))}
            </div>
            <button onClick={simulate} disabled={!selected || loading}
              className="mt-3 flex items-center gap-1.5 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-xs text-white rounded-lg transition-colors"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Play className="h-3.5 w-3.5" />}
              Run Simulation
            </button>
          </div>

          {result && (
            <>
              <div className="border border-[#1a1a1a] rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-xs font-medium text-white">{result.scenario_name}</h2>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded border ${
                    result.confidence === 'high' ? 'text-green-400 border-green-500/30 bg-green-500/10'
                    : result.confidence === 'medium' ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10'
                    : 'text-red-400 border-red-500/30 bg-red-500/10'
                  }`}>
                    {result.confidence} confidence
                  </span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { label: 'Vulnerabilities', cur: result.current.vulnerabilities, proj: result.projected.vulnerabilities, invert: true },
                    { label: 'Critical Vulns', cur: result.current.critical_vulns, proj: result.projected.critical_vulns, invert: true },
                    { label: 'License Risk', cur: result.current.license_risk_score, proj: result.projected.license_risk_score, invert: true, fmt: (v: number) => v.toFixed(1) },
                    { label: 'Health Score', cur: result.current.overall_health, proj: result.projected.overall_health, invert: false, fmt: (v: number) => v.toFixed(1) + '%' },
                  ].map((m: any, i: number) => (
                    <div key={i} className="bg-[#111] rounded-lg p-2.5">
                      <p className="text-[9px] text-gray-600">{m.label}</p>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-xs text-gray-400">{m.cur}{m.fmt ? '' : ''}</span>
                        <ArrowUpDown className="h-3 w-3 text-gray-700" />
                        <span className={`text-xs font-semibold flex items-center gap-0.5 ${deltaColor(result.delta[m.label.toLowerCase().replace(/\s+/g, '_')] || 0, m.invert)}`}>
                          {m.fmt ? m.fmt(m.proj) : m.proj}
                        </span>
                      </div>
                      <div className={`text-[9px] flex items-center gap-0.5 ${deltaColor(result.delta[m.label.toLowerCase().replace(/\s+/g, '_')] || 0, m.invert)}`}>
                        <DeltaIcon val={result.delta[m.label.toLowerCase().replace(/\s+/g, '_')] || 0} invert={m.invert} />
                        {result.delta[m.label.toLowerCase().replace(/\s+/g, '_')] > 0 ? '+' : ''}{result.delta[m.label.toLowerCase().replace(/\s+/g, '_')]}{m.label === 'Health Score' ? '%' : ''}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {result.changes?.length > 0 && (
                <div className="border border-[#1a1a1a] rounded-lg p-3">
                  <h2 className="text-xs font-medium text-white mb-2">Planned Changes ({result.changes.length})</h2>
                  <div className="space-y-1">
                    {result.changes.map((c: any, i: number) => (
                      <div key={i} className="flex items-center gap-2 bg-[#111] rounded p-2 text-[10px]">
                        {c.action === 'remove' ? <X className="h-3 w-3 text-red-400" /> : c.action === 'replace' ? <ArrowUpDown className="h-3 w-3 text-yellow-400" /> : <ArrowUp className="h-3 w-3 text-green-400" />}
                        <span className="text-gray-300 w-24 truncate">{c.package}</span>
                        <span className="text-gray-600">{c.from} →</span>
                        <span className={c.breaking ? 'text-orange-400' : 'text-green-400'}>{c.to || '<removed>'}</span>
                        <span className="text-gray-600 ml-auto">{c.reason}</span>
                        {c.breaking && <span className="text-[8px] text-orange-400 border border-orange-500/30 rounded px-1">BREAKING</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
