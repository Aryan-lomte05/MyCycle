'use client';

import React, { useState } from 'react';
import { Play, RotateCcw, User, AlertCircle, CheckCircle } from 'lucide-react';
import { Button } from './Button';
import { Card } from './Card';
import { SimulatedBadge } from './Badge';
import { db, CycleRecord } from '../db/database';
import { runTier1Detector } from '../../exports/detector';

import persona1 from '../../exports/demo_users/persona_1.json';
import persona2 from '../../exports/demo_users/persona_2.json';
import persona3 from '../../exports/demo_users/persona_3.json';
import persona4 from '../../exports/demo_users/persona_4.json';

const personas = [persona1, persona2, persona3, persona4];

interface DemoModePickerProps {
  onPersonaUpdated: () => void;
}

export const DemoModePicker: React.FC<DemoModePickerProps> = ({ onPersonaUpdated }) => {
  const [selectedPersonaId, setSelectedPersonaId] = useState('persona_1');
  const [stepAdded, setStepAdded] = useState(false);

  const activePersona = personas.find((p) => p.id === selectedPersonaId) || persona1;

  const handleSelectPersona = async (personaId: string) => {
    setSelectedPersonaId(personaId);
    setStepAdded(false);
    const p = personas.find((item) => item.id === personaId) || persona1;

    // Load initial cycles into IndexedDB
    await db.cycles.clear();
    await db.flags.clear();

    for (const c of p.cycles) {
      await db.cycles.put({
        id: c.id,
        start_date: c.start_date,
        cycle_length: c.cycle_length,
        flow_intensity: c.flow_intensity,
        pain_score: c.pain_score,
        symptoms: c.symptoms,
        created_at: new Date().toISOString(),
      });
    }

    // Run detector on baseline cycles
    const all = await db.cycles.orderBy('start_date').toArray();
    const res = runTier1Detector(all);
    if (res.flag_type) {
      await db.flags.put({
        id: 'flag_' + Date.now(),
        cycle_id: all[all.length - 1].id,
        flag_type: res.flag_type,
        contributing_signals: res.contributing_signals,
        created_at: new Date().toISOString(),
      });
    }

    onPersonaUpdated();
  };

  const handleAddNextCycle = async () => {
    if (!activePersona.next_cycle || stepAdded) return;

    const nextC = activePersona.next_cycle;
    await db.cycles.put({
      id: nextC.id,
      start_date: nextC.start_date,
      cycle_length: nextC.cycle_length,
      flow_intensity: nextC.flow_intensity,
      pain_score: nextC.pain_score,
      symptoms: nextC.symptoms,
      created_at: new Date().toISOString(),
    });

    const all = await db.cycles.orderBy('start_date').toArray();
    const res = runTier1Detector(all);

    if (res.flag_type) {
      await db.flags.put({
        id: 'flag_' + Date.now(),
        cycle_id: nextC.id,
        flag_type: res.flag_type,
        contributing_signals: res.contributing_signals,
        created_at: new Date().toISOString(),
      });
    }

    setStepAdded(true);
    onPersonaUpdated();
  };

  const handleResetPersona = async () => {
    await handleSelectPersona(selectedPersonaId);
  };

  return (
    <Card variant="flat" className="p-4 space-y-4 border-2 border-amber-300 bg-amber-50/50">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold text-slate-900 text-sm">
          <User className="w-4 h-4 text-amber-700" />
          Interactive Demo Personas
        </div>
        <SimulatedBadge />
      </div>

      <div className="grid grid-cols-2 gap-2">
        {personas.map((p) => (
          <button
            key={p.id}
            onClick={() => handleSelectPersona(p.id)}
            className={`p-2.5 rounded-xl text-left border transition-all text-xs ${
              selectedPersonaId === p.id
                ? 'border-amber-600 bg-amber-100 font-bold text-amber-950 shadow-2xs'
                : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'
            }`}
          >
            <div>{p.name}</div>
          </button>
        ))}
      </div>

      <p className="text-xs text-slate-600 italic bg-white p-2.5 rounded-lg border">
        {activePersona.description}
      </p>

      <div className="flex gap-2">
        <Button
          variant="amber"
          fullWidth
          size="sm"
          onClick={handleAddNextCycle}
          disabled={stepAdded}
        >
          <Play className="w-4 h-4 mr-1.5" />
          {stepAdded ? 'Next Cycle Added ✓' : 'Add Next Cycle & Run Detector'}
        </Button>

        <Button variant="outline" size="sm" onClick={handleResetPersona}>
          <RotateCcw className="w-4 h-4 mr-1" /> Reset
        </Button>
      </div>
    </Card>
  );
};
