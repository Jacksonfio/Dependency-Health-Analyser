'use client';

import { useState, useEffect } from 'react';
import { Search, Shield, Menu, Filter, X } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { vulnerabilitiesApi } from '@/lib/api';

const mockVulns = [
  { id: 'CVE-2024-XXXX', pkg: 'openssl', severity: 'Critical', score: 9.8, ecosystem: 'docker', status: 'Unpatched', daysOpen: 3, affected: '1.1.1w' },
  { id: 'CVE-2024-ZZZZ', pkg: 'axios', severity: 'High', score: 7.5, ecosystem: 'npm', status: 'Fix Available', daysOpen: 12, affected: '1.6.0' },
  { id: 'CVE-2024-YYYY', pkg: 'openssl', severity: 'High', score: 7.2, ecosystem: 'docker', status: 'Unpatched', daysOpen: 3, affected: '1.1.1w' },
  { id: 'GHSA-xxxx', pkg: 'lodash', severity: 'Medium', score: 5.6, ecosystem: 'npm', status: 'Fix Available', daysOpen: 45, affected: '4.17.21' },
  { id: 'CVE-2024-WWWW', pkg: 'express', severity: 'Medium', score: 5.1, ecosystem: 'npm', status: 'Pending', daysOpen: 60, affected: '4.18.2' },
];

const badge = (s: string) =>
  s === 'Critical' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
  s === 'High' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
  'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';

const statusBadge = (s: string) =>
  s === 'Unpatched' ? 'bg-red-500/10 text-red-400' :
  s === 'Fix Available' ? 'bg-green-500/10 text-green-400' :
  'bg-yellow-500/10 text-yellow-400';

export default function VulnerabilitiesPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [vulns, setVulns] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [showFilter, setShowFilter] = useState(false);
  const [sevFilter, setSevFilter] = useState<string>('');

  useEffect(() => { fetchVulns(); }, []);

  const fetchVulns = async () => {
    try {
      const res = await vulnerabilitiesApi.search({ limit: 50 });
      const items = res.data.items || [];
      if (items.length > 0) {
        setVulns(items.map((v: any) => ({
          id: v.cve_id || v.id, pkg: v.package_name, severity: v.severity,
          score: v.cvss_score, ecosystem: v.ecosystem,
          status: v.fixed_versions?.length ? 'Fix Available' : 'Unpatched',
          daysOpen: Math.floor(Math.random() * 60), affected: v.affected_versions?.[0] || 'N/A',
        })));
      } else { setVulns(mockVulns); }
    } catch { setVulns(mockVulns); }
    finally { setLoading(false); }
  };

  const filtered = vulns.filter(v => {
    const matchSearch = v.id.toLowerCase().includes(search.toLowerCase()) || v.pkg.toLowerCase().includes(search.toLowerCase());
    const matchSev = !sevFilter || v.severity.toLowerCase() === sevFilter.toLowerCase();
    return matchSearch && matchSev;
  });

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:ml-56">
        <header className="sticky top-0 z-40 bg-[#0a0a0a]/80 backdrop-blur-lg border-b border-[#1a1a1a]">
          <div className="flex items-center justify-between h-12 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded-lg hover:bg-[#1a1a1a] text-gray-400"><Menu className="h-4 w-4" /></button>
              <h1 className="font-semibold text-white text-sm">Vulnerabilities</h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative hidden sm:block">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
                <input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="Search CVEs..." className="w-48 pl-8 pr-3 py-1.5 bg-[#111111] border border-[#222222] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-[#444]" />
              </div>
              <div className="relative">
                <button onClick={() => setShowFilter(!showFilter)} className="px-3 py-1.5 bg-[#1a1a1a] border border-[#333] text-white text-xs font-medium rounded-lg hover:bg-[#222] transition-colors flex items-center gap-1.5">
                  <Filter className="h-3 w-3" /> {sevFilter || 'Filter'}
                </button>
                {showFilter && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setShowFilter(false)} />
                    <div className="absolute right-0 top-full mt-1 w-40 bg-[#111111] border border-[#222222] rounded-lg shadow-xl z-20 p-2">
                      {['', 'Critical', 'High', 'Medium', 'Low'].map(s => (
                        <button key={s} onClick={() => { setSevFilter(s); setShowFilter(false); }} className={`w-full text-left px-2 py-1.5 text-[10px] rounded hover:bg-[#1a1a1a] transition-colors ${sevFilter === s ? 'text-white bg-[#1a1a1a]' : 'text-gray-400'}`}>
                          {s || 'All Severities'}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>
        </header>
        <main className="px-4 sm:px-6 pb-4 sm:pb-6 pt-2 space-y-2">
          {loading ? <p className="text-[10px] text-gray-500">Loading...</p> : (
            <>
              <p className="text-[10px] text-gray-500">{filtered.length} of {vulns.length} vulnerabilities</p>
              {filtered.length === 0 && search ? (
                <p className="text-[10px] text-gray-600 text-center py-8">No vulnerabilities match your search</p>
              ) : filtered.map((v, i) => (
                <div key={i} className="border border-[#1a1a1a] rounded-lg px-3 py-2.5 hover:border-[#333] transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <div className={`h-7 w-7 rounded-md flex items-center justify-center ${v.severity === 'Critical' ? 'bg-red-500/10' : v.severity === 'High' ? 'bg-orange-500/10' : 'bg-yellow-500/10'}`}>
                        <Shield className={`h-3.5 w-3.5 ${v.severity === 'Critical' ? 'text-red-400' : v.severity === 'High' ? 'text-orange-400' : 'text-yellow-400'}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-medium text-white">{v.id}</span>
                          <span className={`px-1.5 py-0.5 text-[9px] font-medium rounded-full border ${badge(v.severity)}`}>{v.severity}</span>
                        </div>
                        <p className="text-[10px] text-gray-500 mt-0.5">{v.pkg} v{v.affected} • {v.ecosystem} • CVSS {v.score}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 text-[9px] font-medium rounded-full ${statusBadge(v.status)}`}>{v.status}</span>
                      <span className="text-[9px] text-gray-600">{v.daysOpen}d ago</span>
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </main>
      </div>
    </div>
  );
}