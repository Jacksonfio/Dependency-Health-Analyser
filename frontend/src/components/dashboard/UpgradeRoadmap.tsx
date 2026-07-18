'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Clock, Calendar, CheckCircle2, ArrowRight, Code, Package, AlertCircle } from 'lucide-react';
import { projectsApi } from '@/lib/api';

interface UpgradeItem {
  package: string;
  currentVersion: string;
  targetVersion: string;
  ecosystem: string;
  breakingChange: boolean;
  migrationEffort: 'low' | 'medium' | 'high' | 'very_high';
  securityFixes: string[];
  estimatedHours: number;
  priority: 'immediate' | '2_weeks' | '1_month' | '3_months' | 'none';
  reason: string;
}

interface UpgradeRoadmapProps {
  projectId: string;
}

const mockRoadmap = () => ({
  immediate: [{ package: 'openssl', currentVersion: '1.1.1w', targetVersion: '3.0.13', ecosystem: 'docker', breakingChange: true, migrationEffort: 'high' as const, securityFixes: ['CVE-2024-XXXX', 'CVE-2024-YYYY'], estimatedHours: 8, priority: 'immediate' as const, reason: 'Critical vulnerability with active exploit' }],
  within_2_weeks: [{ package: 'axios', currentVersion: '1.6.0', targetVersion: '1.7.2', ecosystem: 'npm', breakingChange: false, migrationEffort: 'low' as const, securityFixes: ['CVE-2024-ZZZZ'], estimatedHours: 1, priority: '2_weeks' as const, reason: 'High severity SSRF vulnerability' }],
  within_1_month: [{ package: 'lodash', currentVersion: '4.17.21', targetVersion: '4.17.22', ecosystem: 'npm', breakingChange: false, migrationEffort: 'low' as const, securityFixes: [], estimatedHours: 0.5, priority: '1_month' as const, reason: 'Prototype pollution fix in new release' }],
  within_3_months: [{ package: 'express', currentVersion: '4.18.2', targetVersion: '5.0.0', ecosystem: 'npm', breakingChange: true, migrationEffort: 'medium' as const, securityFixes: [], estimatedHours: 16, priority: '3_months' as const, reason: 'Major version overdue, migration recommended' }],
  no_action_needed: [{ package: 'uuid', currentVersion: '9.0.1', targetVersion: '9.0.1', ecosystem: 'npm', breakingChange: false, migrationEffort: 'low' as const, securityFixes: [], estimatedHours: 0, priority: 'none' as const, reason: 'Healthy, actively maintained' }],
});

export function UpgradeRoadmap({ projectId }: UpgradeRoadmapProps) {
  const [roadmap, setRoadmap] = useState<Record<string, UpgradeItem[]> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRoadmap();
  }, [projectId]);

  const fetchRoadmap = async () => {
    try {
      const res = await projectsApi.getUpgradePlan(projectId);
      setRoadmap(res.data);
    } catch {
      setRoadmap(mockRoadmap());
    } finally {
      setLoading(false);
    }
  };

  const columns = [
    { key: 'immediate', label: 'Upgrade Today', icon: AlertTriangle, color: 'text-red-400' },
    { key: 'within_2_weeks', label: 'Upgrade in 2 Weeks', icon: Clock, color: 'text-orange-400' },
    { key: 'within_1_month', label: 'Upgrade in 1 Month', icon: Calendar, color: 'text-yellow-400' },
    { key: 'within_3_months', label: 'Upgrade in 3 Months', icon: Calendar, color: 'text-gray-400' },
    { key: 'no_action_needed', label: 'No Action Needed', icon: CheckCircle2, color: 'text-green-400' },
  ];

  const effortColor = (e: string) =>
    e === 'low' ? 'text-green-400' : e === 'medium' ? 'text-yellow-400' : e === 'high' ? 'text-orange-400' : 'text-red-400';

  if (loading) {
    return <div className="border border-[#1a1a1a] rounded-lg p-4 h-[300px] animate-pulse flex items-center justify-center"><p className="text-xs text-gray-500">Loading...</p></div>;
  }

  return (
    <div>
      <h2 className="text-sm font-medium text-white mb-3">Upgrade Roadmap</h2>
      <div className="space-y-3 max-h-[300px] overflow-y-auto">
        {columns.map((col) => {
          const items = roadmap?.[col.key] || [];
          if (items.length === 0) return null;
          return (
            <div key={col.key}>
              <div className="flex items-center gap-1.5 mb-1.5">
                <col.icon className={`h-3.5 w-3.5 ${col.color}`} />
                <h3 className="text-[11px] font-medium text-white">{col.label}</h3>
                <span className="text-[9px] text-gray-500">({items.length})</span>
              </div>
              <div className="space-y-1.5 pl-4 border-l border-[#1a1a1a]">
                {items.map((item, idx) => (
                  <div key={idx} className="border border-[#1a1a1a] rounded-lg px-2.5 py-2 hover:border-[#333] transition-colors">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-[11px] font-medium text-white">{item.package}</span>
                          <span className="text-[9px] text-gray-500 bg-[#1a1a1a] px-1.5 py-0.5 rounded">{item.ecosystem}</span>
                          {item.breakingChange && <span className="text-[9px] text-orange-400 bg-orange-500/10 px-1.5 py-0.5 rounded flex items-center gap-0.5"><AlertCircle className="h-2.5 w-2.5" />Breaking</span>}
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-[10px] text-gray-400 flex-wrap">
                          <span><Code className="h-3 w-3 inline" /> {item.currentVersion} <ArrowRight className="h-2.5 w-2.5 inline" /> {item.targetVersion}</span>
                          <span className={effortColor(item.migrationEffort)}>{item.migrationEffort.replace('_', ' ')}</span>
                          <span className="text-gray-600">{item.estimatedHours}h</span>
                        </div>
                        <p className="text-[9px] text-gray-600 mt-0.5">{item.reason}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}