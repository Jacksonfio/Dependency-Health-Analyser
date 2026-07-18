'use client';

import { useState, useEffect } from 'react';
import { Menu, Shield, Search, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import api from '@/lib/api';

export default function LicensesPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/v1/licenses/summary').then(r => setData(r.data)).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const riskColor: Record<string, string> = { low: 'text-green-400 bg-green-500/10 border-green-500/30', medium: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30', high: 'text-orange-400 bg-orange-500/10 border-orange-500/30', critical: 'text-red-400 bg-red-500/10 border-red-500/30' };

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:ml-56">
        <header className="sticky top-0 z-40 bg-[#0a0a0a]/80 backdrop-blur-lg border-b border-[#1a1a1a]">
          <div className="flex items-center justify-between h-12 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded-lg hover:bg-[#1a1a1a] text-gray-400"><Menu className="h-4 w-4" /></button>
              <h1 className="font-semibold text-white text-sm">License Compliance</h1>
            </div>
          </div>
        </header>
        <main className="px-4 sm:px-6 pb-4 sm:pb-6 pt-2 space-y-3 max-w-4xl">
          {loading ? <p className="text-[10px] text-gray-500">Loading...</p> : data ? (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Packages</p><p className="text-lg font-semibold text-white">{data.total_packages_analyzed}</p></div>
                <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Risk Score</p><p className="text-lg font-semibold text-white">{data.risk_score}</p></div>
                <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Conflicts</p><p className="text-lg font-semibold text-white">{data.conflicts_detected}</p></div>
                <div className="border border-[#1a1a1a] rounded-lg p-3"><p className="text-[10px] text-gray-500">Critical Risk</p><p className="text-lg font-semibold text-white">{data.risk_summary?.critical || 0}</p></div>
              </div>

              <div className="border border-[#1a1a1a] rounded-lg p-3">
                <h2 className="text-xs font-medium text-white mb-2">Risk Distribution</h2>
                {data.risk_summary && (() => {
                  const total = Object.values(data.risk_summary).reduce((a: number, b: any) => a + (typeof b === 'number' ? b : 0), 0) || 1;
                  const bars = [
                    { label: 'Low', count: data.risk_summary.low || 0, color: 'bg-green-500' },
                    { label: 'Medium', count: data.risk_summary.medium || 0, color: 'bg-yellow-500' },
                    { label: 'High', count: data.risk_summary.high || 0, color: 'bg-orange-500' },
                    { label: 'Critical', count: data.risk_summary.critical || 0, color: 'bg-red-500' },
                  ];
                  return (
                    <div className="space-y-1.5">
                      {bars.map(b => (
                        <div key={b.label} className="flex items-center gap-2">
                          <span className="text-[10px] text-gray-400 w-14">{b.label}</span>
                          <div className="flex-1 h-3 bg-[#1a1a1a] rounded-full overflow-hidden">
                            <div className={`h-full ${b.color} rounded-full transition-all`} style={{ width: `${(b.count / total) * 100}%` }} />
                          </div>
                          <span className="text-[10px] text-gray-500 w-8 text-right">{b.count}</span>
                        </div>
                      ))}
                    </div>
                  );
                })()}
              </div>

              <div className="border border-[#1a1a1a] rounded-lg p-3">
                <h2 className="text-xs font-medium text-white mb-2">License Distribution</h2>
                {data.license_distribution?.length > 0 ? (
                  <div className="space-y-1">
                    {data.license_distribution.map((l: any, i: number) => (
                      <div key={i} className="flex items-center justify-between py-1 border-b border-[#1a1a1a] last:border-0">
                        <div className="flex items-center gap-2">
                          <span className={`px-1.5 py-0.5 rounded text-[9px] border ${riskColor[l.spdx_id] || 'text-gray-400 border-gray-700'}`}>{l.spdx_id}</span>
                          <span className="text-[10px] text-gray-500">{l.count} package{l.count > 1 ? 's' : ''}</span>
                        </div>
                        <span className="text-[10px] text-gray-600">{Math.round((l.count / data.total_packages_analyzed) * 100)}%</span>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-[10px] text-gray-600">No licenses detected</p>}
              </div>

              <div className="border border-[#1a1a1a] rounded-lg p-3">
                <h2 className="text-xs font-medium text-white mb-2">All Packages</h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-[10px]">
                    <thead><tr className="text-gray-600 border-b border-[#1a1a1a]">
                      <th className="text-left py-1.5 pr-2">Package</th>
                      <th className="text-left py-1.5 pr-2">License</th>
                      <th className="text-left py-1.5">Risk</th>
                    </tr></thead>
                    <tbody>
                      {(data.packages || []).map((p: any, i: number) => (
                        <tr key={i} className="border-b border-[#1a1a1a] last:border-0">
                          <td className="py-1.5 pr-2">
                            <span className="text-gray-300">{p.package_name}</span>
                            <span className="text-gray-600 ml-1">{p.version}</span>
                          </td>
                          <td className="py-1.5 pr-2"><span className={`px-1.5 py-0.5 rounded text-[9px] border ${riskColor[p.risk] || 'text-gray-400 border-gray-700'}`}>{p.spdx_id}</span></td>
                          <td className="py-1.5 capitalize text-gray-400">{p.risk}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : <p className="text-[10px] text-gray-500">Failed to load license data</p>}
        </main>
      </div>
    </div>
  );
}
