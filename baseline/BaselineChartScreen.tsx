'use client';

import React, { useMemo } from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, ReferenceArea, ReferenceLine } from 'recharts';
import { Card } from '../components/Card';
import { SimulatedBadge } from '../components/Badge';
import { CycleRecord } from '../db/database';
import { Activity, Info } from 'lucide-react';

interface BaselineChartScreenProps {
  cycles: CycleRecord[];
}

export const BaselineChartScreen: React.FC<BaselineChartScreenProps> = ({ cycles }) => {
  const stats = useMemo(() => {
    if (!cycles || cycles.length === 0) {
      return { mean: 28, stdDev: 2, lowerBand: 24, upperBand: 32, summary: 'No logged cycles yet.' };
    }

    const lengths = cycles.map((c) => c.cycle_length);
    const mean = lengths.reduce((a, b) => a + b, 0) / lengths.length;
    const variance = lengths.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / lengths.length;
    const stdDev = Math.sqrt(variance);

    const lowerBand = Math.max(14, Math.round(mean - 2 * stdDev));
    const upperBand = Math.min(60, Math.round(mean + 2 * stdDev));

    let summary = `Your baseline cycle length is about ${Math.round(mean)} days, with typical variations within ${lowerBand} to ${upperBand} days.`;
    if (stdDev > 5) {
      summary = `Your baseline shows noticeable variation (mean ${Math.round(mean)} days, range ${lowerBand}–${upperBand} days). Continuing to log helps refine your personal band.`;
    }

    return { mean: Math.round(mean * 10) / 10, stdDev: Math.round(stdDev * 10) / 10, lowerBand, upperBand, summary };
  }, [cycles]);

  const chartData = useMemo(() => {
    return cycles.map((c, idx) => ({
      index: idx + 1,
      date: c.start_date,
      length: c.cycle_length,
      mean: stats.mean,
      lowerBand: stats.lowerBand,
      upperBand: stats.upperBand,
      isLatest: idx === cycles.length - 1,
    }));
  }, [cycles, stats]);

  return (
    <div className="space-y-6 pb-24 max-w-md mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900">Personal Baseline Band</h2>
        <SimulatedBadge />
      </div>

      <Card variant="flat" className="p-4 space-y-4">
        <div className="flex items-center justify-between text-xs text-slate-600 border-b border-slate-200 pb-2">
          <span>Target Mean: <strong className="text-slate-900">{stats.mean} days</strong></span>
          <span>Personal Band (±2 SD): <strong className="text-slate-900">{stats.lowerBand} - {stats.upperBand} days</strong></span>
        </div>

        {/* Chart Container */}
        <div className="h-64 w-full bg-white p-2 rounded-xl border border-slate-200">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 15, right: 15, left: -20, bottom: 5 }}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis domain={[15, 50]} tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      return (
                        <div className="bg-slate-900 text-white p-2.5 rounded-lg text-xs shadow-md">
                          <div className="font-bold">{data.date}</div>
                          <div>Cycle Length: {data.length} days</div>
                          {data.isLatest && <div className="text-amber-400 font-semibold mt-0.5">Current Highlighted Cycle</div>}
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                {/* Normal variance band highlight */}
                <ReferenceArea y1={stats.lowerBand} y2={stats.upperBand} fill="#ccfbf1" fillOpacity={0.4} />
                <ReferenceLine y={stats.mean} stroke="#0d9488" strokeDasharray="4 4" />
                <Line
                  type="monotone"
                  dataKey="length"
                  stroke="#0f766e"
                  strokeWidth={3}
                  dot={(props: any) => {
                    const { cx, cy, payload } = props;
                    if (payload.isLatest) {
                      return <circle key="dot-latest" cx={cx} cy={cy} r={6} fill="#f59e0b" stroke="#ffffff" strokeWidth={2} />;
                    }
                    return <circle key={`dot-${payload.index}`} cx={cx} cy={cy} r={4} fill="#0f766e" />;
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-500 italic">
              Insufficient data for baseline visualization. Log at least 2 cycles.
            </div>
          )}
        </div>

        {/* Plain language summary sentence */}
        <div className="bg-teal-50 border border-teal-200 rounded-xl p-3 flex items-start gap-2.5 text-xs text-teal-900">
          <Info className="w-4 h-4 text-teal-700 shrink-0 mt-0.5" />
          <div>{stats.summary}</div>
        </div>
      </Card>
    </div>
  );
};
