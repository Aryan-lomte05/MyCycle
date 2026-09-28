'use client';

import React from 'react';
import { AlertCircle, Volume2, Share2, Stethoscope, ChevronRight } from 'lucide-react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { SimulatedBadge } from '../components/Badge';

interface FlagScreenProps {
  flagType: string | null;
  contributingSignals: string[];
  messages: any;
  onOpenMythCard: () => void;
  onShareWithTrust: () => void;
}

export const FlagScreen: React.FC<FlagScreenProps> = ({
  flagType,
  contributingSignals,
  messages,
  onOpenMythCard,
  onShareWithTrust,
}) => {
  const flagDetails = flagType ? messages?.flags?.[flagType] : null;

  if (!flagType || !flagDetails) {
    return (
      <div className="space-y-4 max-w-md mx-auto pb-24">
        <h2 className="text-xl font-bold text-slate-900">Screening Status</h2>
        <Card variant="teal">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-teal-100 rounded-full text-teal-800">
              <Stethoscope className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-slate-900 text-sm">No Active Screening Flags</div>
              <p className="text-xs text-slate-600 mt-0.5">
                Your logged cycles are currently within your usual personal baseline parameters.
              </p>
            </div>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-md mx-auto pb-24">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-slate-900">Screening Flag Details</h2>
        <SimulatedBadge />
      </div>

      {/* Flag Alert Card - Warm Amber ("Worth a look") */}
      <Card variant="amber" className="border-2 border-amber-300">
        <div className="flex items-start gap-3 mb-3">
          <div className="p-2.5 bg-amber-500 text-white rounded-xl shrink-0">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-amber-800 bg-amber-100 px-2 py-0.5 rounded-md">
              Screening Pattern
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-1">{flagDetails.title}</h3>
          </div>
        </div>

        <p className="text-sm text-slate-800 leading-relaxed font-medium bg-white/80 p-3 rounded-xl border border-amber-200 mb-4">
          {flagDetails.explanation}
        </p>

        {/* Contributing Signals */}
        <div className="mb-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-amber-900 mb-2">
            Contributing Pattern Signals
          </h4>
          <ul className="space-y-1.5">
            {(contributingSignals.length > 0 ? contributingSignals : flagDetails.contributing_signals).map(
              (sig: string, idx: number) => (
                <li key={idx} className="text-xs text-slate-800 flex items-start gap-2 bg-white/60 p-2 rounded-lg">
                  <span className="text-amber-600 font-bold">•</span>
                  <span>{sig}</span>
                </li>
              )
            )}
          </ul>
        </div>

        {/* Doctor Consultation Disclaimer */}
        <div className="bg-amber-100/90 border border-amber-300 rounded-xl p-3 flex items-center gap-2.5 text-xs text-amber-950 font-bold">
          <Stethoscope className="w-5 h-5 text-amber-800 shrink-0" />
          <span>{messages.consult_doctor}</span>
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="space-y-3">
        <Button variant="primary" fullWidth size="md" onClick={onOpenMythCard}>
          <Volume2 className="w-4 h-4 mr-2" />
          Listen to Audio Myth & Fact Card
        </Button>

        <Button variant="outline" fullWidth size="md" onClick={onShareWithTrust}>
          <Share2 className="w-4 h-4 mr-2" />
          Share this with someone I trust
        </Button>
      </div>
    </div>
  );
};
