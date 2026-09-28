'use client';

import React, { useState } from 'react';
import { Printer, QrCode, Stethoscope, CheckSquare, Square } from 'lucide-react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { CycleRecord } from '../db/database';

interface DoctorVisitCardScreenProps {
  cycles: CycleRecord[];
  messages: any;
}

export const DoctorVisitCardScreen: React.FC<DoctorVisitCardScreenProps> = ({ cycles, messages }) => {
  const [includeBaseline, setIncludeBaseline] = useState(true);
  const [includeHistory, setIncludeHistory] = useState(true);
  const [includeSymptoms, setIncludeSymptoms] = useState(true);

  const meanLength = cycles.length > 0
    ? Math.round(cycles.reduce((a, b) => a + b.cycle_length, 0) / cycles.length)
    : 28;

  const handlePrint = () => {
    window.print();
  };

  const compactQrData = JSON.stringify({
    app: 'MyCycle',
    type: 'ScreeningSummary',
    mean_length: meanLength,
    n_cycles: cycles.length,
    latest_date: cycles[cycles.length - 1]?.start_date || 'N/A',
  });

  return (
    <div className="space-y-6 max-w-md mx-auto pb-24">
      {/* Screen Options (hidden during print) */}
      <div className="print:hidden space-y-4">
        <div className="flex items-center gap-2">
          <Stethoscope className="w-6 h-6 text-teal-700" />
          <h2 className="text-xl font-bold text-slate-900">Doctor Visit Summary Card</h2>
        </div>

        <Card variant="flat" className="p-4 space-y-3">
          <h3 className="font-bold text-slate-900 text-sm">Select Sections to Include in Summary</h3>
          <div className="space-y-2 text-xs font-semibold">
            <button
              type="button"
              onClick={() => setIncludeBaseline(!includeBaseline)}
              className="flex items-center gap-2 text-slate-800"
            >
              {includeBaseline ? <CheckSquare className="w-4 h-4 text-teal-700" /> : <Square className="w-4 h-4 text-slate-400" />}
              <span>Include Baseline Mean & SD Range</span>
            </button>
            <button
              type="button"
              onClick={() => setIncludeHistory(!includeHistory)}
              className="flex items-center gap-2 text-slate-800"
            >
              {includeHistory ? <CheckSquare className="w-4 h-4 text-teal-700" /> : <Square className="w-4 h-4 text-slate-400" />}
              <span>Include Recent Cycles Log History</span>
            </button>
            <button
              type="button"
              onClick={() => setIncludeSymptoms(!includeSymptoms)}
              className="flex items-center gap-2 text-slate-800"
            >
              {includeSymptoms ? <CheckSquare className="w-4 h-4 text-teal-700" /> : <Square className="w-4 h-4 text-slate-400" />}
              <span>Include Aggregated Symptom Frequencies</span>
            </button>
          </div>

          <Button variant="primary" fullWidth size="lg" onClick={handlePrint} className="mt-2">
            <Printer className="w-5 h-5 mr-2" />
            Print / Export PDF Summary
          </Button>
        </Card>
      </div>

      {/* Printable Sheet (styled specifically for print) */}
      <div className="bg-white border-2 border-slate-300 p-6 rounded-2xl shadow-md space-y-4 print:border-none print:shadow-none print:p-0">
        <div className="border-b border-slate-200 pb-3 flex justify-between items-start">
          <div>
            <h1 className="text-xl font-black text-slate-900">MyCycle Screening Summary</h1>
            <p className="text-xs text-slate-500">Self-tracked longitudinal cycle report</p>
          </div>
          <div className="text-right text-[10px] text-slate-400">
            Generated: {new Date().toLocaleDateString()}
          </div>
        </div>

        {includeBaseline && (
          <div className="bg-slate-50 p-3 rounded-xl border text-xs space-y-1">
            <div className="font-bold text-slate-900">Personal Baseline Metrics</div>
            <div>Historical Mean Cycle Length: <strong>{meanLength} days</strong></div>
            <div>Total Cycles Tracked: <strong>{cycles.length} cycles</strong></div>
          </div>
        )}

        {includeHistory && (
          <div className="space-y-2">
            <div className="text-xs font-bold text-slate-900">Recent Cycles Logged</div>
            <table className="w-full text-[11px] text-left border-collapse border border-slate-200">
              <thead>
                <tr className="bg-slate-100 text-slate-800 font-bold border-b">
                  <th className="p-1.5 border">Start Date</th>
                  <th className="p-1.5 border">Length</th>
                  <th className="p-1.5 border">Flow (1-4)</th>
                  <th className="p-1.5 border">Pain (0-10)</th>
                </tr>
              </thead>
              <tbody>
                {cycles.slice(-4).map((c) => (
                  <tr key={c.id} className="border-b">
                    <td className="p-1.5 border">{c.start_date}</td>
                    <td className="p-1.5 border">{c.cycle_length} d</td>
                    <td className="p-1.5 border">{c.flow_intensity}</td>
                    <td className="p-1.5 border">{c.pain_score}/10</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Compact Summary QR Code String */}
        <div className="bg-slate-100 p-3 rounded-xl border text-[10px] font-mono text-slate-700 flex items-center gap-3">
          <QrCode className="w-8 h-8 text-slate-800 shrink-0" />
          <div className="break-all">
            <strong>Compact QR Data String (&lt;500 B):</strong> {compactQrData}
          </div>
        </div>

        {/* Mandatory Footer Disclaimer */}
        <div className="border-t border-slate-200 pt-3 text-[11px] font-semibold text-slate-600 text-center leading-snug">
          Screening summary from a self-tracking app, not a medical record. Please consult a doctor.
        </div>
      </div>
    </div>
  );
};
