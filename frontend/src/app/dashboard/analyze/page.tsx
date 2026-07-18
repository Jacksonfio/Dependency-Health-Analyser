'use client';

import { useState, useCallback } from 'react';
import { Menu, Github, Upload, ExternalLink, AlertTriangle, Shield, Users, TrendingUp, GitBranch, Activity, ArrowUp, ArrowDown, Minus, Search, FileText, CheckCircle, XCircle } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import api from '@/lib/api';

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

const FACTOR_ICONS: Record<string, any> = {
  'Maintainer Risk': Users, 'Security Risk': Shield,
  'Release Health': Activity, 'Community Health': TrendingUp, 'Breaking Change Risk': GitBranch,
};

export default function AnalyzePage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tab, setTab] = useState<'github' | 'upload'>('github');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState('');
  const [selectedDep, setSelectedDep] = useState<any>(null);

  const analyzeGithub = useCallback(async () => {
    if (!url.trim()) return;
    setLoading(true); setError(''); setResult(null); setSelectedDep(null);
    try {
      const form = new FormData();
      form.append('url', url);
      const res = await api.post('/api/v1/analyze/github', form);
      setResult(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to analyze repository');
    }
    setLoading(false);
  }, [url]);

  const analyzeUpload = useCallback(async () => {
    if (!file) return;
    setLoading(true); setError(''); setResult(null); setSelectedDep(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await api.post('/api/v1/analyze/upload', form);
      setResult(res.data);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to analyze file');
    }
    setLoading(false);
  }, [file]);

  const results = result?.analysis?.results || [];
  const summary = result?.analysis?.summary || {};

  return (
    <div className="min-h-screen bg-surface">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:ml-56">
        <header className="sticky top-0 z-40 bg-surface/80 backdrop-blur-lg border-b border-border bg-gradient-header">
          <div className="flex items-center justify-between h-12 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded-lg hover:bg-stone-800/40 text-stone-400"><Menu className="h-4 w-4" /></button>
              <h1 className="font-semibold text-stone-100 text-sm">Dependency Analyzer</h1>
            </div>
            <div className="flex items-center gap-2 bg-card border border-border rounded-lg p-0.5">
              <button onClick={() => setTab('github')} className={`px-3 py-1.5 text-[10px] rounded-md transition-all ${tab === 'github' ? 'bg-stone-700/60 text-amber-300' : 'text-stone-500 hover:text-stone-300'}`}><Github className="h-3 w-3 inline mr-1" />GitHub</button>
              <button onClick={() => setTab('upload')} className={`px-3 py-1.5 text-[10px] rounded-md transition-all ${tab === 'upload' ? 'bg-stone-700/60 text-amber-300' : 'text-stone-500 hover:text-stone-300'}`}><Upload className="h-3 w-3 inline mr-1" />Upload</button>
            </div>
          </div>
        </header>
        <main className="px-4 sm:px-6 pb-4 sm:pb-6 pt-2 space-y-2">
          <p className="text-[10px] text-muted">Paste a GitHub URL or upload a dependency file to analyze risk across all packages</p>

          {/* Input section */}
          <div className="card bg-gradient-card p-4">
            {tab === 'github' ? (
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Github className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-500" />
                  <input type="text" placeholder="https://github.com/vercel/next.js" value={url}
                    onChange={e => setUrl(e.target.value)}
                    className="w-full bg-card border border-border rounded-lg pl-9 pr-3 py-2 text-xs text-stone-100 placeholder-stone-600 focus:outline-none focus:border-amber-700 focus:ring-1 focus:ring-amber-500/20 transition-colors" />
                </div>
                <button onClick={analyzeGithub} disabled={loading || !url.trim()}
                  className="btn-primary disabled:opacity-40 flex items-center gap-1.5">
                  {loading ? <Activity className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}
                  Analyze
                </button>
              </div>
            ) : (
              <div className="flex gap-2 items-center">
                <label className="flex-1 flex items-center gap-2 bg-card border border-border rounded-lg px-3 py-2 cursor-pointer hover:border-amber-700/40 transition-colors">
                  <Upload className="h-3.5 w-3.5 text-stone-500" />
                  <span className={`text-xs ${file ? 'text-stone-100' : 'text-stone-600'}`}>
                    {file ? file.name : 'package.json, requirements.txt, pom.xml...'}
                  </span>
                  <input type="file" accept=".json,.txt,.xml,Pipfile" onChange={e => setFile(e.target.files?.[0] || null)} className="hidden" />
                </label>
                <button onClick={analyzeUpload} disabled={loading || !file}
                  className="btn-primary disabled:opacity-40 flex items-center gap-1.5">
                  {loading ? <Activity className="h-3 w-3 animate-spin" /> : <Search className="h-3 w-3" />}
                  Analyze
                </button>
              </div>
            )}
          </div>

          {error && (
            <div className="flex items-center gap-2 p-3 bg-rose-900/20 border border-rose-800/30 rounded-lg">
              <AlertTriangle className="h-3.5 w-3.5 text-rose-400 flex-shrink-0" />
              <p className="text-xs text-rose-300">{error}</p>
            </div>
          )}

          {loading && (
            <div className="card p-12 flex items-center justify-center">
              <div className="flex flex-col items-center gap-2">
                <Activity className="h-5 w-5 text-amber-500/60 animate-spin" />
                <p className="text-xs text-muted">Analyzing dependencies...</p>
              </div>
            </div>
          )}

          {result && !loading && (
            <>
              {/* Result header */}
              {result.repo && (
                <div className="card rounded-lg p-3 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Github className="h-4 w-4 text-gray-400" />
                    <span className="text-sm font-medium text-white">{result.repo}</span>
                    <span className="text-[9px] text-gray-600 bg-[#111] px-1.5 py-0.5 rounded">{result.files_found?.length || 0} files</span>
                  </div>
                  <a href={result.url} target="_blank" className="text-gray-500 hover:text-gray-300"><ExternalLink className="h-3.5 w-3.5" /></a>
                </div>
              )}
              {result.filename && (
                <div className="card rounded-lg p-3 flex items-center gap-2">
                  <FileText className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-white">{result.filename}</span>
                  <span className="text-[9px] text-gray-600 bg-[#111] px-1.5 py-0.5 rounded">{result.dependencies_found?.length || 0} deps</span>
                </div>
              )}

              {/* Summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Dependencies</p>
                  <p className="text-lg font-bold text-white mt-0.5">{summary.total_dependencies}</p>
                </div>
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Avg Risk</p>
                  <p className="text-lg font-bold mt-0.5" style={{ color: getRiskColor(summary.average_risk) }}>{summary.average_risk}%</p>
                </div>
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Critical</p>
                  <p className="text-lg font-bold text-red-400 mt-0.5">{summary.critical}</p>
                </div>
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Urgent Upgrades</p>
                  <p className="text-lg font-bold mt-0.5" style={{ color: summary.urgent_upgrades > 0 ? '#ef4444' : '#22c55e' }}>{summary.urgent_upgrades}</p>
                </div>
                <div className="card rounded-lg p-3">
                  <p className="text-[10px] text-gray-500">Ecosystem</p>
                  <p className="text-sm font-medium text-white mt-0.5">{result.ecosystem || (result.files_found?.[0]?.ecosystem || 'N/A')}</p>
                </div>
              </div>

              {/* Main content: table + detail */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
                {/* Dependency table */}
                <div className="card rounded-lg">
                  <div className="px-3 py-2 border-b border-border">
                    <h2 className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Dependencies</h2>
                  </div>
                  <div className="divide-y divide-[#1a1a1a] max-h-[400px] overflow-y-auto">
                    {results.map((dep: any) => (
                      <button key={dep.name} onClick={() => setSelectedDep(dep)}
                        className={`w-full text-left px-3 py-2 hover:bg-[#111111] transition-colors flex items-center justify-between ${selectedDep?.name === dep.name ? 'bg-[#111111]' : ''}`}>
                        <div className="flex items-center gap-2 min-w-0">
                          <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0`} style={{ backgroundColor: getRiskColor(dep.risk_score) }} />
                          <span className="text-xs text-gray-300 truncate">{dep.name}</span>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <span className="text-[9px] text-gray-600">{dep.ecosystem}</span>
                          <span className="text-xs font-medium" style={{ color: getRiskColor(dep.risk_score) }}>{dep.risk_score ?? '—'}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Detail panel */}
                <div className="card rounded-lg">
                  <div className="px-3 py-2 border-b border-border">
                    <h2 className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">
                      {selectedDep ? selectedDep.name : 'Select a dependency'}
                    </h2>
                  </div>
                  {selectedDep ? (
                    <div className="p-3 space-y-2.5 overflow-y-auto max-h-[400px]">
                      {/* Score & ML */}
                      <div className="grid grid-cols-3 gap-2">
                        <div className="bg-[#111111] rounded-lg p-2 text-center">
                          <p className="text-[9px] text-gray-600">Risk</p>
                          <p className="text-base font-bold" style={{ color: getRiskColor(selectedDep.risk_score) }}>{selectedDep.risk_score ?? '—'}</p>
                        </div>
                        <div className="bg-[#111111] rounded-lg p-2 text-center">
                          <p className="text-[9px] text-gray-600">Projected</p>
                          <p className="text-base font-bold" style={{ color: getRiskColor(selectedDep.ml_prediction?.projected_risk_90d) }}>{selectedDep.ml_prediction?.projected_risk_90d ?? '—'}</p>
                        </div>
                        <div className="bg-[#111111] rounded-lg p-2 text-center">
                          <p className="text-[9px] text-gray-600">Level</p>
                          <span className="inline-block text-[9px] font-medium mt-1 px-1.5 py-0.5 rounded"
                            style={{ backgroundColor: getRiskColor(selectedDep.risk_score) + '20', color: getRiskColor(selectedDep.risk_score) }}>
                            {(selectedDep.risk_level || 'unknown').toUpperCase()}
                          </span>
                        </div>
                      </div>

                      {/* Factors */}
                      <div className="space-y-1.5">
                        {selectedDep.factors?.map((f: any) => {
                          const Icon = FACTOR_ICONS[f.name] || Activity;
                          return (
                            <div key={f.name} className="flex items-center gap-2">
                              <Icon className="h-3 w-3 text-gray-500 flex-shrink-0" />
                              <div className="flex-1 min-w-0">
                                <div className="flex justify-between items-center">
                                  <span className="text-[9px] text-gray-500">{f.name}</span>
                                  <span className="text-[9px] font-medium" style={{ color: getRiskColor(f.score) }}>{f.score}</span>
                                </div>
                                <div className="h-1 bg-[#1a1a1a] rounded-full mt-0.5">
                                  <div className="h-full rounded-full" style={{ width: `${f.score}%`, backgroundColor: getRiskColor(f.score) }} />
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Explanations */}
                      {selectedDep.explanation?.recommendations?.length > 0 && (
                        <div className="bg-[#111111] rounded-lg p-2">
                          <p className="text-[9px] text-gray-500 mb-1">Recommendations</p>
                          <ul className="space-y-0.5">
                            {selectedDep.explanation.recommendations.map((r: string, i: number) => (
                              <li key={i} className="flex items-start gap-1 text-[10px] text-gray-400">
                                <ArrowUp className="h-2.5 w-2.5 text-green-400 mt-0.5 flex-shrink-0" />{r}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-6 flex items-center justify-center text-gray-600">
                      <p className="text-[11px]">Click a dependency to see details</p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}

          {!result && !loading && (
            <div className="border border-dashed border-[#222222] rounded-lg p-12 flex flex-col items-center justify-center">
              {tab === 'github' ? <Github className="h-8 w-8 text-gray-700 mb-2" /> : <Upload className="h-8 w-8 text-gray-700 mb-2" />}
              <p className="text-xs text-gray-600">{tab === 'github' ? 'Paste a public GitHub repository URL above' : 'Upload a package.json, requirements.txt, or pom.xml'}</p>
              <p className="text-[9px] text-gray-700 mt-1">We\'ll analyze every dependency with live data + AI risk prediction</p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
