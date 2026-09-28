'use client';

import React, { useState } from 'react';
import { Users, Key, ShieldCheck, Heart, Info, Copy, Check, Eye } from 'lucide-react';
import { Card } from '../components/Card';
import { Button } from '../components/Button';
import { SimulatedBadge } from '../components/Badge';

interface FamilyViewScreenProps {
  currentPhase: 'follicular' | 'ovulatory' | 'luteal' | 'menstrual';
  userRole: 'self' | 'partner' | 'parent' | 'sibling';
  todayTips: any;
  onRoleChange: (role: 'self' | 'partner' | 'parent' | 'sibling') => void;
}

export const FamilyViewScreen: React.FC<FamilyViewScreenProps> = ({
  currentPhase,
  userRole,
  todayTips,
  onRoleChange,
}) => {
  const [inviteCode, setInviteCode] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [selectedRoleForCode, setSelectedRoleForCode] = useState<'partner' | 'parent' | 'sibling'>('partner');

  const handleGenerateCode = () => {
    const code = Math.random().toString(36).substring(2, 8).toUpperCase();
    setInviteCode(`MC-${code}-${selectedRoleForCode.toUpperCase().slice(0, 3)}`);
  };

  const handleCopyCode = () => {
    if (inviteCode) {
      navigator.clipboard.writeText(inviteCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const phaseNames = {
    follicular: 'Follicular Phase (Rising Energy)',
    ovulatory: 'Ovulatory Phase (Peak Phase)',
    luteal: 'Luteal Phase (Progesterone Phase)',
    menstrual: 'Menstrual Phase (Rest & Recovery)',
  };

  const tipText = todayTips?.[currentPhase]?.[userRole === 'self' ? 'partner' : userRole] ||
    'Supportive environment and balanced nutrition are always helpful.';

  return (
    <div className="space-y-5 max-w-md mx-auto pb-24">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users className="w-6 h-6 text-teal-700" />
          <h2 className="text-xl font-bold text-slate-900">Family Circle View</h2>
        </div>
        <SimulatedBadge />
      </div>

      {/* Role Toggle Switcher for Demo Preview */}
      <div className="bg-slate-100 p-1.5 rounded-xl border border-slate-200 flex text-xs font-semibold">
        {(['self', 'partner', 'parent', 'sibling'] as const).map((r) => (
          <button
            key={r}
            onClick={() => onRoleChange(r)}
            className={`flex-1 py-1.5 rounded-lg capitalize transition-all ${
              userRole === r ? 'bg-teal-700 text-white shadow-xs' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Companion Banner if viewing as companion */}
      {userRole !== 'self' && (
        <Card variant="teal" className="border-teal-500">
          <div className="flex items-start gap-2.5">
            <Eye className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-teal-950 text-sm">Companion View Active</div>
              <p className="text-xs text-teal-800 mt-0.5">
                You can see current cycle phase and support tips only. Raw logs and screening flags are kept strictly private on the user's phone.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Today Support Card (FR15) */}
      <Card variant="default" className="border-2 border-teal-600 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-bold uppercase tracking-wider text-teal-800 bg-teal-100 px-2.5 py-1 rounded-md">
            Today Support Tip ({userRole.toUpperCase()})
          </span>
          <Heart className="w-5 h-5 text-teal-700 fill-teal-100" />
        </div>

        <h3 className="text-lg font-bold text-slate-900">{phaseNames[currentPhase]}</h3>

        <div className="bg-slate-50 border border-slate-200 p-4 rounded-xl text-sm text-slate-800 leading-relaxed font-medium">
          "{tipText}"
        </div>
      </Card>

      {/* Visibility Matrix Table */}
      <Card variant="flat" className="p-4 space-y-3">
        <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-teal-700" />
          Visibility Matrix (Privacy Guarantees)
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left text-slate-700 border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-slate-900 font-bold">
                <th className="py-2 pr-2">Item</th>
                <th className="py-2 px-1 text-center">Self</th>
                <th className="py-2 px-1 text-center">Partner</th>
                <th className="py-2 px-1 text-center">Parent</th>
                <th className="py-2 px-1 text-center">Sibling</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              <tr>
                <td className="py-2 pr-2">Raw Logs</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-slate-400">✗</td>
                <td className="py-2 px-1 text-center text-slate-400">✗</td>
                <td className="py-2 px-1 text-center text-slate-400">✗</td>
              </tr>
              <tr>
                <td className="py-2 pr-2">Screening Flags</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-slate-400">✗</td>
                <td className="py-2 px-1 text-center text-slate-400">✗</td>
                <td className="py-2 px-1 text-center text-slate-400">✗</td>
              </tr>
              <tr>
                <td className="py-2 pr-2">Cycle Phase</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
              </tr>
              <tr>
                <td className="py-2 pr-2">Coarse Window</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-slate-400">✗</td>
              </tr>
              <tr>
                <td className="py-2 pr-2">Support Tips</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
                <td className="py-2 px-1 text-center text-teal-700 font-bold">✓</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>

      {/* Invite Flow (Self only) */}
      {userRole === 'self' && (
        <Card variant="flat" className="p-4 space-y-3">
          <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
            <Key className="w-4 h-4 text-teal-700" />
            Generate Family Circle Code
          </h3>

          <div className="flex gap-2">
            {(['partner', 'parent', 'sibling'] as const).map((r) => (
              <button
                key={r}
                onClick={() => setSelectedRoleForCode(r)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize border ${
                  selectedRoleForCode === r
                    ? 'border-teal-600 bg-teal-50 text-teal-900'
                    : 'border-slate-300 bg-white text-slate-700'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <Button variant="primary" fullWidth size="md" onClick={handleGenerateCode}>
            Generate 24h Access Code
          </Button>

          {inviteCode && (
            <div className="bg-slate-900 text-white p-3 rounded-xl flex items-center justify-between font-mono text-sm border border-slate-800">
              <span className="text-emerald-400 font-bold tracking-widest">{inviteCode}</span>
              <button
                onClick={handleCopyCode}
                className="p-1.5 text-slate-300 hover:text-white flex items-center gap-1 text-xs"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};
