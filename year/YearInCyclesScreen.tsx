'use client';

import React from 'react';
import { Calendar, Award, Sparkles } from 'lucide-react';
import { Card } from '../components/Card';
import { CycleRecord } from '../db/database';

interface YearInCyclesScreenProps {
  cycles: CycleRecord[];
}

export const YearInCyclesScreen: React.FC<YearInCyclesScreenProps> = ({ cycles }) => {
  const totalTracked = cycles.length;
  const avgLength = totalTracked > 0
    ? Math.round(cycles.reduce((a, b) => a + b.cycle_length, 0) / totalTracked)
    : 28;

  return (
    <div className="space-y-5 max-w-md mx-auto pb-24">
      <div className="flex items-center gap-2">
        <Sparkles className="w-6 h-6 text-teal-700" />
        <h2 className="text-xl font-bold text-slate-900">Year in Cycles Summary</h2>
      </div>

      <Card variant="teal" className="p-6 text-center space-y-4 border-2 border-teal-600">
        <Award className="w-12 h-12 text-teal-700 mx-auto" />
        <h3 className="text-2xl font-black text-slate-900">{totalTracked} Cycles Tracked</h3>
        <p className="text-xs text-teal-950 font-medium leading-relaxed">
          Your personal baseline average is <strong>{avgLength} days</strong>. You have logged symptoms and cycle metrics privately on this device.
        </p>

        <div className="pt-2 text-[11px] text-slate-500 italic">
          Card saved locally on device • Zero network upload
        </div>
      </Card>
    </div>
  );
};
