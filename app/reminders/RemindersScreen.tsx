'use client';

import React from 'react';
import { Bell, Apple, ShieldAlert, HeartPulse } from 'lucide-react';
import { Card } from '../components/Card';
import { SimulatedBadge } from '../components/Badge';

export const RemindersScreen: React.FC = () => {
  const reminders = [
    {
      id: 'r1',
      title: 'Expected Period Window',
      detail: 'Expected in 3 days (± 2 days uncertainty range)',
      category: 'cycle',
      icon: Bell,
    },
    {
      id: 'r2',
      title: 'Iron-Rich Nutrition Nudge (Anemia Prevention)',
      detail: 'Consider spinach, lentils, jaggery, and Vitamin C to support hemoglobin during flow.',
      category: 'food',
      icon: Apple,
    },
    {
      id: 'r3',
      title: 'Hydration & Comfort Tip',
      detail: 'Drink 2.5L warm water daily. Herbal chamomile or ginger tea helps ease uterine tension.',
      category: 'comfort',
      icon: HeartPulse,
    },
  ];

  return (
    <div className="space-y-5 max-w-md mx-auto pb-24">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell className="w-6 h-6 text-teal-700" />
          <h2 className="text-xl font-bold text-slate-900">Reminders & Food Nudges</h2>
        </div>
        <SimulatedBadge />
      </div>

      <div className="space-y-3">
        {reminders.map((r) => {
          const Icon = r.icon;
          const isFood = r.category === 'food';

          return (
            <Card
              key={r.id}
              variant={isFood ? 'amber' : 'flat'}
              className="flex items-start gap-3 p-4"
            >
              <div className={`p-2.5 rounded-xl shrink-0 ${isFood ? 'bg-amber-500 text-white' : 'bg-teal-100 text-teal-800'}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <div className="font-bold text-slate-900 text-sm">{r.title}</div>
                <p className="text-xs text-slate-700 mt-1 leading-relaxed">{r.detail}</p>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
};
