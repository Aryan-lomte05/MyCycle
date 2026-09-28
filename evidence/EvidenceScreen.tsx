'use client';

import React, { useEffect, useState } from 'react';
import { Card } from '../components/Card';
import { SimulatedBadge } from '../components/Badge';
import summaryData from '../../results/summary.json';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { Award, Lock, Clock } from 'lucide-react';

export const EvidenceScreen: React.FC = () => {
  const [data, setData] = useState<any>(summaryData);

  return (
    <div className="space-y-6 max-w-md mx-auto pb-24">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900">Evidence & Benchmarks</h2>
        <SimulatedBadge label={`Simulated (n=${data.n_participants})`} />
      </div>

      <p className="text-xs text-slate-600 bg-amber-50 p-3 rounded-xl border border-amber-200 leading-relaxed">
        {data.note}. All evaluation metrics represent synthetic baseline comparisons.
      </p>

      {/* 1. Model Comparison */}
      <Card variant="flat" className="p-4 space-y-3">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <Award className="w-4 h-4 text-teal-700" />
          Model Detection Accuracy (F1-Score)
        </h3>

        <div className="h-52 w-full bg-white p-2 rounded-xl border border-slate-200">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.model_comparison} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="model" tick={{ fontSize: 9, fill: '#64748b' }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip />
              <Bar dataKey="f1_score" fill="#0d9488" radius={[6, 6, 0, 0]} name="F1-Score" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 2. Privacy vs Utility */}
      <Card variant="flat" className="p-4 space-y-3">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <Lock className="w-4 h-4 text-teal-700" />
          Differential Privacy (Epsilon vs F1-Score)
        </h3>

        <div className="h-48 w-full bg-white p-2 rounded-xl border border-slate-200">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.privacy_utility} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="clipping" tick={{ fontSize: 9, fill: '#64748b' }} />
              <YAxis domain={[0.5, 1]} tick={{ fontSize: 10, fill: '#64748b' }} />
              <Tooltip />
              <Bar dataKey="f1_score" fill="#f59e0b" radius={[6, 6, 0, 0]} name="F1-Score" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {/* 3. Detection Delay */}
      <Card variant="flat" className="p-4 space-y-3">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <Clock className="w-4 h-4 text-teal-700" />
          Detection Speed (Cycle Offset)
        </h3>

        <div className="space-y-2 text-xs">
          {data.detection_delay.map((d: any) => (
            <div key={d.cycle_offset} className="flex items-center justify-between bg-white p-2.5 rounded-lg border">
              <span className="font-medium text-slate-800">Detected in {d.cycle_offset} cycle(s)</span>
              <span className="font-bold text-teal-700">{Math.round(d.detection_rate * 100)}% Rate</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};
