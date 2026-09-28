'use client';

import React, { useState } from 'react';
import { Shield, CheckCircle2, User, Users, Heart, GraduationCap } from 'lucide-react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { db, UserSettings } from '../db/database';

interface OnboardingScreenProps {
  onComplete: (settings: UserSettings) => void;
  messages: any;
}

export const OnboardingScreen: React.FC<OnboardingScreenProps> = ({ onComplete, messages }) => {
  const [lang, setLang] = useState<'en' | 'hi' | 'mr'>('en');
  const [role, setRole] = useState<'self' | 'partner' | 'parent' | 'sibling'>('self');

  const handleFinish = async () => {
    const updatedSettings: UserSettings = {
      id: 'current',
      language: lang,
      role,
      privacy_accepted: true,
      disguise_enabled: false,
    };

    await db.settings.put(updatedSettings);
    onComplete(updatedSettings);
  };

  const roles = [
    { id: 'self', label: 'Self (Track my cycle)', icon: User, desc: 'Full personal tracking, screening flags & insights' },
    { id: 'partner', label: 'Partner', icon: Heart, desc: 'Phase overview & tips on how to support' },
    { id: 'parent', label: 'Parent / Guardian', icon: Users, desc: 'Phase overview & nutrition support tips' },
    { id: 'sibling', label: 'Sibling / Family', icon: GraduationCap, desc: 'Supportive guidance & educational cards' },
  ];

  return (
    <div className="min-h-screen bg-slate-50 p-4 sm:p-6 max-w-md mx-auto flex flex-col justify-between">
      <div>
        {/* Header with Language Switcher */}
        <div className="flex items-center justify-between mb-6 pt-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-teal-700 flex items-center justify-center text-white font-bold">
              M
            </div>
            <span className="font-bold text-slate-900 text-lg">{messages.app_name}</span>
          </div>
          <LanguageSwitcher currentLang={lang} onSelect={setLang} />
        </div>

        {/* Privacy Promise Banner */}
        <Card variant="teal" className="mb-6">
          <div className="flex items-start gap-3">
            <Shield className="w-6 h-6 text-teal-700 shrink-0 mt-0.5" />
            <div>
              <h2 className="font-bold text-slate-900 text-base mb-1">Privacy First Promise</h2>
              <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
                {messages.privacy_promise} No account or signup is required.
              </p>
            </div>
          </div>
        </Card>

        {/* Role Choice */}
        <div className="mb-6">
          <h3 className="font-bold text-slate-900 text-base mb-3">Choose Your Role</h3>
          <div className="space-y-3">
            {roles.map((r) => {
              const Icon = r.icon;
              const isSelected = role === r.id;

              return (
                <div
                  key={r.id}
                  onClick={() => setRole(r.id as any)}
                  className={`p-4 rounded-xl border-2 transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? 'border-teal-600 bg-teal-50/60 shadow-xs'
                      : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                  role="radio"
                  aria-checked={isSelected}
                  tabIndex={0}
                >
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${isSelected ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-600'}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-semibold text-slate-900 text-sm">{r.label}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{r.desc}</div>
                    </div>
                  </div>
                  {isSelected && <CheckCircle2 className="w-5 h-5 text-teal-700 shrink-0" />}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Start Button */}
      <div className="pt-4 pb-6">
        <Button variant="primary" fullWidth size="lg" onClick={handleFinish}>
          Get Started Privately
        </Button>
      </div>
    </div>
  );
};
