'use client';

import { Shield, AlertTriangle, ArrowUpRight, ArrowDownRight, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProjectSummary {
  id: string;
  name: string;
  ecosystem: string;
  overallScore: number;
  criticalVulns: number;
  highVulns: number;
  mediumVulns: number;
  lowVulns: number;
  totalDeps: number;
  outdatedDeps: number;
  lastScanned: string;
  riskTrend: 'improving' | 'stable' | 'degrading';
}

interface ProjectHealthCardProps {
  project: ProjectSummary;
}

export function ProjectHealthCard({ project }: ProjectHealthCardProps) {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-400 from-green-500/10 border-green-500/20';
    if (score >= 60) return 'text-yellow-400 from-yellow-500/10 border-yellow-500/20';
    if (score >= 40) return 'text-orange-400 from-orange-500/10 border-orange-500/20';
    return 'text-red-400 from-red-500/10 border-red-500/20';
  };

  const getScoreBg = (score: number) => {
    if (score >= 80) return 'bg-green-500/10 text-green-400';
    if (score >= 60) return 'bg-yellow-500/10 text-yellow-400';
    if (score >= 40) return 'bg-orange-500/10 text-orange-400';
    return 'bg-red-500/10 text-red-400';
  };

  const getScoreLabel = (score: number) => {
    if (score >= 80) return 'Healthy';
    if (score >= 60) return 'Warning';
    if (score >= 40) return 'At Risk';
    return 'Critical';
  };

  const scoreStyle = getScoreColor(project.overallScore);

  return (
    <div className={cn(
      'group bg-gradient-to-br to-transparent rounded-2xl border p-6 card-lift',
      'from-gray-800/5 border-white/5 hover:border-white/10'
    )}>
      <div className="flex items-start justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className={cn(
            'h-10 w-10 rounded-xl flex items-center justify-center',
            project.ecosystem === 'npm' && 'bg-red-500/15',
            project.ecosystem === 'pypi' && 'bg-amber-500/15',
            project.ecosystem === 'maven' && 'bg-green-500/15',
          )}>
            <span className={cn(
              'text-sm font-bold',
              project.ecosystem === 'npm' && 'text-red-400',
              project.ecosystem === 'pypi' && 'text-amber-400',
              project.ecosystem === 'maven' && 'text-green-400',
            )}>
              {project.ecosystem === 'npm' ? 'N' : project.ecosystem === 'pypi' ? 'P' : 'M'}
            </span>
          </div>
          <div>
            <h3 className="font-bold text-white group-hover:text-primary-200 transition-colors">{project.name}</h3>
            <p className="text-xs text-gray-500 capitalize">{project.ecosystem}</p>
          </div>
        </div>
        <div className="text-right">
          <p className={cn('text-3xl font-bold', getScoreColor(project.overallScore).split(' ')[0])}>
            {project.overallScore}%
          </p>
          <span className={cn('px-2.5 py-1 text-xs font-medium rounded-full', getScoreBg(project.overallScore))}>
            {getScoreLabel(project.overallScore)}
          </span>
        </div>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Vulnerabilities</span>
          <div className="flex items-center gap-2">
            {project.criticalVulns > 0 && (
              <span className="px-2.5 py-1 text-xs bg-red-500/10 text-red-400 rounded-full font-medium">
                {project.criticalVulns} Critical
              </span>
            )}
            {project.highVulns > 0 && (
              <span className="px-2.5 py-1 text-xs bg-orange-500/10 text-orange-400 rounded-full font-medium">
                {project.highVulns} High
              </span>
            )}
            {project.criticalVulns === 0 && project.highVulns === 0 && (
              <span className="text-xs text-green-400 font-medium">None</span>
            )}
          </div>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Outdated Deps</span>
          <span className="font-medium text-white">
            <span className={cn(
              project.outdatedDeps > 30 ? 'text-red-400' :
              project.outdatedDeps > 15 ? 'text-yellow-400' : 'text-green-400'
            )}>
              {project.outdatedDeps}
            </span>
            <span className="text-gray-500">/{project.totalDeps}</span>
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Last Scanned</span>
          <span className="text-gray-400">{project.lastScanned}</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-500">Risk Trend</span>
          <div className="flex items-center gap-1.5">
            {project.riskTrend === 'improving' && <ArrowUpRight className="h-4 w-4 text-green-400" />}
            {project.riskTrend === 'degrading' && <ArrowDownRight className="h-4 w-4 text-red-400" />}
            {project.riskTrend === 'stable' && <Shield className="h-4 w-4 text-gray-400" />}
            <span className="capitalize text-gray-300 font-medium">{project.riskTrend}</span>
          </div>
        </div>
      </div>
    </div>
  );
}