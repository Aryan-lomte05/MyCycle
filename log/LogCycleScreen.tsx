'use client';

import React, { useState, useEffect } from 'react';
import { Calendar, Trash2, Edit2, Save, Plus, AlertCircle, Droplets, Activity } from 'lucide-react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { db, CycleRecord } from '../db/database';
import { runTier1Detector } from '../../exports/detector';

interface LogCycleScreenProps {
  onCycleSaved: () => void;
  messages: any;
}

const DEFAULT_SYMPTOMS = [
  'Cramps',
  'Headache',
  'Bloating',
  'Fatigue',
  'Mood Swings',
  'Backache',
  'Acne',
  'Nausea',
];

export const LogCycleScreen: React.FC<LogCycleScreenProps> = ({ onCycleSaved, messages }) => {
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [cycleLength, setCycleLength] = useState(28);
  const [flowIntensity, setFlowIntensity] = useState(2); // 1-4
  const [painScore, setPainScore] = useState(3); // 0-10
  const [selectedSymptoms, setSelectedSymptoms] = useState<Record<string, number>>({});
  const [pastCycles, setPastCycles] = useState<CycleRecord[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);

  const loadPastCycles = async () => {
    const list = await db.cycles.orderBy('start_date').toArray();
    setPastCycles(list);
  };

  useEffect(() => {
    loadPastCycles();
  }, []);

  const handleSymptomToggle = (symptom: string) => {
    setSelectedSymptoms((prev) => {
      const currentSeverity = prev[symptom] || 0;
      const nextSeverity = (currentSeverity + 1) % 5; // 0, 1, 2, 3, 4
      const copy = { ...prev };
      if (nextSeverity === 0) {
        delete copy[symptom];
      } else {
        copy[symptom] = nextSeverity;
      }
      return copy;
    });
  };

  const handleSave = async () => {
    const symptomList = Object.entries(selectedSymptoms).map(
      ([sym, sev]) => `${sym.toLowerCase()} (level ${sev})`
    );

    const record: CycleRecord = {
      id: editingId || 'cycle_' + Date.now(),
      start_date: startDate,
      cycle_length: Number(cycleLength),
      flow_intensity: Number(flowIntensity),
      pain_score: Number(painScore),
      symptoms: symptomList,
      created_at: new Date().toISOString(),
    };

    await db.cycles.put(record);

    // Re-run screening detector on updated history
    const allCycles = await db.cycles.orderBy('start_date').toArray();
    const detectorResult = runTier1Detector(allCycles);

    if (detectorResult.flag_type) {
      await db.flags.put({
        id: 'flag_' + Date.now(),
        cycle_id: record.id,
        flag_type: detectorResult.flag_type,
        contributing_signals: detectorResult.contributing_signals,
        created_at: new Date().toISOString(),
      });
    }

    setEditingId(null);
    setSelectedSymptoms({});
    await loadPastCycles();
    onCycleSaved();
  };

  const handleDelete = async (id: string) => {
    await db.cycles.delete(id);
    await loadPastCycles();
    onCycleSaved();
  };

  const handleEdit = (c: CycleRecord) => {
    setEditingId(c.id);
    setStartDate(c.start_date);
    setCycleLength(c.cycle_length);
    setFlowIntensity(c.flow_intensity);
    setPainScore(c.pain_score);
  };

  const flowLabels = ['Spotting', 'Light', 'Medium', 'Heavy'];
  const severityNames = ['None', 'Mild', 'Moderate', 'Severe', 'Intense'];

  return (
    <div className="space-y-6 pb-24 max-w-md mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900">
          {editingId ? 'Edit Cycle Log' : 'Log Cycle Entry'}
        </h2>
        {editingId && (
          <Button variant="outline" size="sm" onClick={() => setEditingId(null)}>
            Cancel Edit
          </Button>
        )}
      </div>

      <Card variant="flat" className="space-y-4">
        {/* Start Date & Cycle Length */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full p-2.5 rounded-xl border border-slate-300 bg-white text-sm font-medium text-slate-800"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Cycle Length (Days)
            </label>
            <input
              type="number"
              min="14"
              max="60"
              value={cycleLength}
              onChange={(e) => setCycleLength(Number(e.target.value))}
              className="w-full p-2.5 rounded-xl border border-slate-300 bg-white text-sm font-medium text-slate-800"
            />
          </div>
        </div>

        {/* Flow Intensity Buttons */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-2">
            Flow Intensity (4-Step Scale)
          </label>
          <div className="grid grid-cols-4 gap-2">
            {[1, 2, 3, 4].map((step) => (
              <button
                key={step}
                type="button"
                onClick={() => setFlowIntensity(step)}
                className={`py-3 px-1 rounded-xl text-center border-2 transition-all min-h-[52px] ${
                  flowIntensity === step
                    ? 'border-teal-700 bg-teal-100/70 text-teal-900 font-bold'
                    : 'border-slate-200 bg-white text-slate-700'
                }`}
              >
                <Droplets
                  className={`w-4 h-4 mx-auto mb-1 ${
                    flowIntensity >= step ? 'text-teal-700 fill-teal-600' : 'text-slate-300'
                  }`}
                />
                <span className="text-[11px] block">{flowLabels[step - 1]}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Pain Slider 0-10 */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="text-xs font-semibold text-slate-700">Pain Score (0 - 10)</label>
            <span className="text-sm font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
              {painScore} / 10
            </span>
          </div>
          <input
            type="range"
            min="0"
            max="10"
            value={painScore}
            onChange={(e) => setPainScore(Number(e.target.value))}
            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-teal-700"
          />
        </div>

        {/* 8 Symptom Chips with 4 Severity Steps */}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-2">
            Symptoms (Tap to increase severity 1-4)
          </label>
          <div className="flex flex-wrap gap-2">
            {DEFAULT_SYMPTOMS.map((sym) => {
              const sev = selectedSymptoms[sym] || 0;
              return (
                <button
                  key={sym}
                  type="button"
                  onClick={() => handleSymptomToggle(sym)}
                  className={`px-3 py-2 rounded-xl text-xs font-medium border transition-all flex items-center gap-1.5 min-h-[44px] ${
                    sev > 0
                      ? 'bg-teal-700 text-white border-teal-800 font-semibold shadow-xs'
                      : 'bg-white text-slate-700 border-slate-300 hover:border-slate-400'
                  }`}
                >
                  <span>{sym}</span>
                  {sev > 0 && (
                    <span className="bg-teal-900 text-teal-100 text-[10px] px-1.5 py-0.5 rounded-full">
                      {severityNames[sev]}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Save Button */}
        <Button variant="primary" fullWidth size="lg" onClick={handleSave}>
          <Save className="w-5 h-5 mr-2" />
          {editingId ? 'Update Cycle Log' : 'Save Cycle Log Privately'}
        </Button>
      </Card>

      {/* Past Cycles History */}
      <div>
        <h3 className="font-bold text-slate-900 text-sm mb-3">Logged Cycle History ({pastCycles.length})</h3>
        {pastCycles.length === 0 ? (
          <p className="text-xs text-slate-500 italic bg-white p-4 rounded-xl border border-dashed text-center">
            No cycles logged yet. Log your first cycle or enable demo mode!
          </p>
        ) : (
          <div className="space-y-2.5">
            {pastCycles.map((c) => (
              <div
                key={c.id}
                className="bg-white p-3.5 rounded-xl border border-slate-200 flex items-center justify-between shadow-2xs"
              >
                <div>
                  <div className="font-bold text-slate-900 text-sm">{c.start_date}</div>
                  <div className="text-xs text-slate-600 mt-0.5">
                    {c.cycle_length} days • Flow: level {c.flow_intensity} • Pain: {c.pain_score}/10
                  </div>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleEdit(c)}
                    className="p-2 text-slate-500 hover:text-teal-700 min-h-[44px] min-w-[44px] flex items-center justify-center"
                    title="Edit cycle"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(c.id)}
                    className="p-2 text-slate-500 hover:text-rose-600 min-h-[44px] min-w-[44px] flex items-center justify-center"
                    title="Delete cycle"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
