'use client';

import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Area,
} from 'recharts';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { projectsApi } from '@/lib/api';

interface RiskDataPoint {
  day: number;
  date: string;
  projectedRisk: number;
  actualRisk?: number;
  confidence: number;
  projected: boolean;
}

interface RiskTimelineChartProps {
  projectId?: string;
  days?: number;
}

export function RiskTimelineChart({ projectId, days = 90 }: RiskTimelineChartProps) {
  const [data, setData] = useState<RiskDataPoint[]>([]);
  const [currentRisk, setCurrentRisk] = useState(0);
  const [projectedRisk, setProjectedRisk] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRiskTimeline();
  }, [projectId, days]);

  const fetchRiskTimeline = async () => {
    try {
      if (!projectId) throw new Error('no projectId');
      const res = await projectsApi.getRiskTimeline(projectId, { days });
      setData(res.data.timeline || []);
      setCurrentRisk(res.data.current_risk || 0);
      setProjectedRisk(res.data.projected_risk_90d || 0);
    } catch {
      setData(generateMockData(days));
      setCurrentRisk(42);
      setProjectedRisk(72);
    } finally {
      setLoading(false);
    }
  };

  const generateMockData = (d: number): RiskDataPoint[] => {
    const points: RiskDataPoint[] = [];
    const baseRisk = 35 + Math.random() * 20;
    const trend = (Math.random() - 0.3) * 0.5;
    for (let i = 0; i <= d; i += Math.max(1, Math.floor(d / 12))) {
      const date = new Date();
      date.setDate(date.getDate() + i);
      const risk = Math.min(100, Math.max(0, baseRisk + trend * i * 1.5 + Math.sin(i / 10) * 5));
      points.push({
        day: i,
        date: date.toISOString().split('T')[0],
        projectedRisk: Math.round(risk),
        confidence: Math.max(0.5, 1 - (i / d) * 0.4),
        projected: i > 0,
      });
    }
    return points;
  };

  const riskChange = projectedRisk - currentRisk;
  const trendIcon = riskChange > 5 ? <TrendingUp className="h-5 w-5 text-red-400" />
    : riskChange < -5 ? <TrendingDown className="h-5 w-5 text-green-400" />
    : <Minus className="h-5 w-5 text-gray-500" />;

  const getRiskColor = (risk: number) => {
    if (risk >= 75) return '#ef4444';
    if (risk >= 50) return '#f97316';
    if (risk >= 25) return '#eab308';
    return '#22c55e';
  };

  if (loading) {
    return (
      <div className="border border-[#1a1a1a] rounded-lg p-4 h-[300px] animate-pulse flex items-center justify-center">
        <p className="text-xs text-gray-500">Loading...</p>
      </div>
    );
  }

  const chartData = data.map((d) => ({
    date: d.date,
    projected: d.projectedRisk,
    actual: d.actualRisk,
    confidenceUpper: Math.min(100, d.projectedRisk + (1 - d.confidence) * 20),
    confidenceLower: Math.max(0, d.projectedRisk - (1 - d.confidence) * 20),
  }));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-medium text-white">Risk Trajectory</h2>
          <p className="text-[10px] text-gray-500 mt-0.5">Projected dependency health risk over {days} days</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-lg font-bold text-white" style={{ color: getRiskColor(currentRisk) }}>{currentRisk}%</p>
            <p className="text-[9px] text-gray-500">Current</p>
          </div>
          <div className="w-px h-8 bg-[#1a1a1a]" />
          {trendIcon}
          <div className="w-px h-8 bg-[#1a1a1a]" />
          <div className="text-right">
            <p className="text-lg font-bold text-white" style={{ color: getRiskColor(projectedRisk) }}>{projectedRisk}%</p>
            <p className="text-[9px] text-gray-500">Projected</p>
          </div>
        </div>
      </div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
            <XAxis dataKey="date" tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickCount={6} />
            <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickCount={4} />
            <Tooltip contentStyle={{ backgroundColor: '#111', border: '1px solid #222', borderRadius: '8px', padding: '8px 12px' }} labelStyle={{ color: '#e5e7eb', fontWeight: 600 }} formatter={(value: number) => [`${value}%`, 'Risk Score']} />
            <Legend wrapperStyle={{ paddingTop: '4px' }} formatter={(value) => <span className="text-gray-400 text-[10px]">{value}</span>} />
            <Area type="monotone" dataKey="confidenceUpper" stroke="transparent" fill="#ef4444" fillOpacity={0.06} isAnimationActive={false} />
            <Area type="monotone" dataKey="confidenceLower" stroke="transparent" fill="#ef4444" fillOpacity={0.06} isAnimationActive={false} />
            <Line type="monotone" dataKey="actual" stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: '#3b82f6', fill: '#1e3a5f' }} name="Actual Risk" />
            <Line type="monotone" dataKey="projected" stroke="#ef4444" strokeWidth={2} strokeDasharray="6 3" dot={false} activeDot={{ r: 4, strokeWidth: 2, stroke: '#ef4444', fill: '#5f1e1e' }} name="Projected Risk" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}