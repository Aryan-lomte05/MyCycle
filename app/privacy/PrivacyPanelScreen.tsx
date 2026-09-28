'use client';

import React, { useState, useEffect } from 'react';
import { ShieldCheck, HardDrive, Lock, RefreshCw, Trash2, Network, Cpu } from 'lucide-react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { getNetworkMetrics, simulateFederatedRound, resetNetworkMetrics } from '../lib/netClient';
import { db } from '../db/database';

interface PrivacyPanelScreenProps {
  onDataCleared: () => void;
  messages: any;
}

export const PrivacyPanelScreen: React.FC<PrivacyPanelScreenProps> = ({ onDataCleared, messages }) => {
  const [metrics, setMetrics] = useState(getNetworkMetrics());
  const [federatedLog, setFederatedLog] = useState<any | null>(null);
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(getNetworkMetrics());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleRunFederated = () => {
    const res = simulateFederatedRound();
    setFederatedLog(res);
    setMetrics(getNetworkMetrics());
  };

  const handleDeleteAll = async () => {
    await db.cycles.clear();
    await db.flags.clear();
    resetNetworkMetrics();
    setMetrics(getNetworkMetrics());
    setShowConfirmDelete(false);
    onDataCleared();
  };

  return (
    <div className="space-y-5 max-w-md mx-auto pb-24">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-6 h-6 text-teal-700" />
        <h2 className="text-xl font-bold text-slate-900">Privacy & Transparency Panel</h2>
      </div>

      {/* Real Live Counter (FR13 / L9) */}
      <Card variant="teal" className="border-2 border-teal-600 p-4">
        <div className="text-xs font-bold uppercase tracking-wider text-teal-800 mb-1">
          Live Network Privacy Audit
        </div>
        <div className="text-2xl font-black text-slate-900 mb-1">
          Data sent to our servers: <span className="text-teal-700">{metrics.userLogBytesSent} bytes</span>
        </div>
        <p className="text-xs text-slate-600 leading-snug">
          Real-time count of sensitive cycle log bytes transmitted over the network. Always zero by design.
        </p>

        <div className="mt-3 pt-3 border-t border-teal-200 grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-slate-500">Content Fetches:</span>{' '}
            <strong className="text-slate-800">{metrics.contentBytes} B</strong>
          </div>
          <div>
            <span className="text-slate-500">Model Updates:</span>{' '}
            <strong className="text-slate-800">{metrics.modelUpdateBytes} B</strong>
          </div>
        </div>
      </Card>

      {/* 3 Core Privacy Blocks */}
      <div className="space-y-3">
        <Card variant="flat" className="flex items-start gap-3 p-3.5">
          <HardDrive className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-slate-900 text-sm">1. Stored On This Phone</div>
            <p className="text-xs text-slate-600 mt-0.5">
              All cycle logs, symptoms, and pain scores live exclusively in IndexedDB inside your browser.
            </p>
          </div>
        </Card>

        <Card variant="flat" className="flex items-start gap-3 p-3.5">
          <Lock className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-slate-900 text-sm">2. Never Leaves Your Device</div>
            <p className="text-xs text-slate-600 mt-0.5">
              Screening algorithms execute entirely on-device (Tier 1 baseline + local ONNX engine).
            </p>
          </div>
        </Card>

        <Card variant="flat" className="flex items-start gap-3 p-3.5">
          <Cpu className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
          <div>
            <div className="font-bold text-slate-900 text-sm">3. Optional Privacy-Preserving Model Update</div>
            <p className="text-xs text-slate-600 mt-0.5">
              Optional differential privacy aggregation sending noisy gradient updates (disabled by default).
            </p>
          </div>
        </Card>
      </div>

      {/* Federated Demo Round */}
      <Card variant="flat" className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="font-bold text-slate-900 text-sm flex items-center gap-2">
            <Network className="w-4 h-4 text-teal-700" />
            Federated Learning Demo
          </div>
          <Button variant="secondary" size="sm" onClick={handleRunFederated}>
            <RefreshCw className="w-3.5 h-3.5 mr-1" /> Run Demo Round
          </Button>
        </div>

        {federatedLog && (
          <div className="bg-slate-900 text-slate-100 p-3 rounded-xl text-xs space-y-1 font-mono">
            <div className="text-emerald-400 font-bold">✓ Federated Round Executed</div>
            <div>Update Size: {federatedLog.bytesSentKB} KB</div>
            <div>Clipping: {federatedLog.clipping}</div>
            <div>Noise: {federatedLog.noise}</div>
            <div className="text-amber-300 italic pt-1">{federatedLog.note}</div>
          </div>
        )}
      </Card>

      {/* Delete All Data */}
      <div className="pt-2">
        {showConfirmDelete ? (
          <Card variant="flat" className="border-rose-300 bg-rose-50 p-4 space-y-3">
            <div className="font-bold text-rose-900 text-sm">Are you sure you want to delete all local data?</div>
            <p className="text-xs text-rose-700">This action permanently clears all cycle logs and flags from your device.</p>
            <div className="flex gap-2">
              <Button variant="danger" size="sm" onClick={handleDeleteAll}>
                Yes, Delete Everything
              </Button>
              <Button variant="outline" size="sm" onClick={() => setShowConfirmDelete(false)}>
                Cancel
              </Button>
            </div>
          </Card>
        ) : (
          <Button variant="outline" fullWidth size="md" className="text-rose-700 border-rose-300 hover:bg-rose-50" onClick={() => setShowConfirmDelete(true)}>
            <Trash2 className="w-4 h-4 mr-2" />
            Delete All Local Data
          </Button>
        )}
      </div>
    </div>
  );
};
