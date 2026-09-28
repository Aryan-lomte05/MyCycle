'use client';

import React, { useState, useEffect } from 'react';
import { Shield, Bell, HelpCircle, Stethoscope, Sparkles, Mic, FileText, Lock } from 'lucide-react';
import { Card } from './Card';
import { Button } from './Button';
import { SimulatedBadge } from './Badge';
import { LanguageSwitcher } from './LanguageSwitcher';
import { BottomNav } from './BottomNav';
import { DemoModePicker } from './DemoModePicker';
import { OnboardingScreen } from '../onboarding/OnboardingScreen';
import { LogCycleScreen } from '../log/LogCycleScreen';
import { BaselineChartScreen } from '../baseline/BaselineChartScreen';
import { FlagScreen } from '../flags/FlagScreen';
import { MythCardScreen } from '../myths/MythCardScreen';
import { PrivacyPanelScreen } from '../privacy/PrivacyPanelScreen';
import { FamilyViewScreen } from '../family/FamilyViewScreen';
import { RemindersScreen } from '../reminders/RemindersScreen';
import { EvidenceScreen } from '../evidence/EvidenceScreen';
import { DoctorVisitCardScreen } from '../doctor/DoctorVisitCardScreen';
import { VoiceLoggingScreen } from '../voice/VoiceLoggingScreen';
import { YearInCyclesScreen } from '../year/YearInCyclesScreen';
import { CalculatorSkin } from '../disguise/CalculatorSkin';
import { db, UserSettings, CycleRecord, ensureUserSettings } from '../db/database';
import { runTier1Detector } from '../../exports/detector';

import messagesEn from '../../content/en/messages.json';
import messagesHi from '../../content/hi/messages.json';
import messagesMr from '../../content/mr/messages.json';
import todayTipsEn from '../../content/en/today_tips.json';
import todayTipsHi from '../../content/hi/today_tips.json';
import todayTipsMr from '../../content/mr/today_tips.json';

const messageMap = { en: messagesEn, hi: messagesHi, mr: messagesMr };
const tipsMap = { en: todayTipsEn, hi: todayTipsHi, mr: todayTipsMr };

export const MainApp: React.FC = () => {
  const [settings, setSettings] = useState<UserSettings | null>(null);
  const [cycles, setCycles] = useState<CycleRecord[]>([]);
  const [activeTab, setActiveTab] = useState('home');
  const [isDisguised, setIsDisguised] = useState(false);
  const [latestFlag, setLatestFlag] = useState<any | null>(null);

  const loadAll = async () => {
    const s = await ensureUserSettings();
    setSettings(s);

    const cList = await db.cycles.orderBy('start_date').toArray();
    setCycles(cList);

    const flagList = await db.flags.orderBy('created_at').reverse().toArray();
    if (flagList.length > 0) {
      setLatestFlag(flagList[0]);
    } else {
      setLatestFlag(null);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleLanguageChange = async (lang: 'en' | 'hi' | 'mr') => {
    if (!settings) return;
    const updated = { ...settings, language: lang };
    await db.settings.put(updated);
    setSettings(updated);
  };

  const handleRoleChange = async (role: 'self' | 'partner' | 'parent' | 'sibling') => {
    if (!settings) return;
    const updated = { ...settings, role };
    await db.settings.put(updated);
    setSettings(updated);
  };

  const currentLang = settings?.language || 'en';
  const messages = messageMap[currentLang];
  const todayTips = tipsMap[currentLang];

  if (!settings) return null;

  // Onboarding check
  if (!settings.privacy_accepted) {
    return (
      <OnboardingScreen
        onComplete={(newSettings) => setSettings(newSettings)}
        messages={messages}
      />
    );
  }

  // Calculator Disguise check
  if (isDisguised || settings.disguise_enabled) {
    return (
      <CalculatorSkin
        savedPinHash={settings.disguise_pin_hash}
        onSetPinHash={async (hash) => {
          const updated = { ...settings, disguise_pin_hash: hash, disguise_enabled: true };
          await db.settings.put(updated);
          setSettings(updated);
        }}
        onUnlockSuccess={() => setIsDisguised(false)}
      />
    );
  }

  // Calculate phase and next period expected date
  const lastCycle = cycles.length > 0 ? cycles[cycles.length - 1] : null;
  let nextExpectedPeriod = 'Log cycles to calculate window';
  let currentPhase: 'follicular' | 'ovulatory' | 'luteal' | 'menstrual' = 'follicular';

  if (lastCycle) {
    const startDate = new Date(lastCycle.start_date);
    const meanLen = Math.round(
      cycles.reduce((a, b) => a + b.cycle_length, 0) / cycles.length
    );
    const nextDate = new Date(startDate.getTime() + meanLen * 86400000);
    nextExpectedPeriod = `${nextDate.toISOString().split('T')[0]} (± 2 days)`;

    const daysDiff = Math.floor((Date.now() - startDate.getTime()) / 86400000);
    if (daysDiff <= 5) currentPhase = 'menstrual';
    else if (daysDiff <= 13) currentPhase = 'follicular';
    else if (daysDiff <= 16) currentPhase = 'ovulatory';
    else currentPhase = 'luteal';
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans pb-24 max-w-md mx-auto relative shadow-xl">
      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 px-4 py-3 sticky top-0 z-30 flex items-center justify-between shadow-2xs">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-teal-700 text-white font-bold flex items-center justify-center text-sm">
            M
          </div>
          <span className="font-bold text-slate-900">{messages.app_name}</span>
        </div>

        <div className="flex items-center gap-2">
          <SimulatedBadge />
          <LanguageSwitcher currentLang={currentLang} onSelect={handleLanguageChange} />
        </div>
      </header>

      {/* Main Tab Content */}
      <main className="p-4 sm:p-5">
        {activeTab === 'home' && (
          <div className="space-y-5">
            {/* Phase & Prediction Banner */}
            <Card variant="teal" className="p-5 space-y-3">
              <div className="flex justify-between items-center text-xs font-bold uppercase tracking-wider text-teal-800">
                <span>Current Phase</span>
                <span className="bg-teal-200 text-teal-900 px-2 py-0.5 rounded-md">
                  {currentPhase}
                </span>
              </div>

              <h2 className="text-xl font-bold text-slate-900">
                Expected Next Period Window
              </h2>

              <div className="text-sm font-semibold text-slate-800 bg-white/80 p-3 rounded-xl border border-teal-200">
                {nextExpectedPeriod}
              </div>
            </Card>

            {/* Latest Flag Card if exists */}
            {latestFlag && (
              <Card variant="amber" className="p-4 border-amber-300 space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-amber-800">
                  Screening Flag Notice
                </div>
                <div className="font-bold text-slate-900 text-base">
                  {messages?.flags?.[latestFlag.flag_type]?.title || 'Screening Flag Detected'}
                </div>
                <Button
                  variant="amber"
                  size="sm"
                  onClick={() => setActiveTab('flags')}
                  className="mt-1"
                >
                  View Screening Flag Details
                </Button>
              </Card>
            )}

            {/* Interactive Demo Mode Card */}
            <DemoModePicker onPersonaUpdated={loadAll} />

            {/* Feature Shortcuts Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              <button
                onClick={() => setActiveTab('voice')}
                className="p-3 bg-white rounded-xl border border-slate-200 text-left hover:border-teal-500 transition-all flex items-center gap-2.5"
              >
                <Mic className="w-5 h-5 text-teal-700 shrink-0" />
                <span className="text-xs font-semibold text-slate-800">Voice Logging</span>
              </button>

              <button
                onClick={() => setActiveTab('doctor')}
                className="p-3 bg-white rounded-xl border border-slate-200 text-left hover:border-teal-500 transition-all flex items-center gap-2.5"
              >
                <FileText className="w-5 h-5 text-teal-700 shrink-0" />
                <span className="text-xs font-semibold text-slate-800">Doctor Summary</span>
              </button>

              <button
                onClick={() => setActiveTab('reminders')}
                className="p-3 bg-white rounded-xl border border-slate-200 text-left hover:border-teal-500 transition-all flex items-center gap-2.5"
              >
                <Bell className="w-5 h-5 text-teal-700 shrink-0" />
                <span className="text-xs font-semibold text-slate-800">Food Nudges</span>
              </button>

              <button
                onClick={() => setActiveTab('evidence')}
                className="p-3 bg-white rounded-xl border border-slate-200 text-left hover:border-teal-500 transition-all flex items-center gap-2.5"
              >
                <Sparkles className="w-5 h-5 text-teal-700 shrink-0" />
                <span className="text-xs font-semibold text-slate-800">Evidence Stats</span>
              </button>
            </div>
          </div>
        )}

        {activeTab === 'log' && (
          <LogCycleScreen onCycleSaved={loadAll} messages={messages} />
        )}

        {activeTab === 'baseline' && <BaselineChartScreen cycles={cycles} />}

        {activeTab === 'flags' && (
          <FlagScreen
            flagType={latestFlag?.flag_type || null}
            contributingSignals={latestFlag?.contributing_signals || []}
            messages={messages}
            onOpenMythCard={() => setActiveTab('myths')}
            onShareWithTrust={() => setActiveTab('family')}
          />
        )}

        {activeTab === 'myths' && <MythCardScreen messages={messages} />}

        {activeTab === 'privacy' && (
          <PrivacyPanelScreen onDataCleared={loadAll} messages={messages} />
        )}

        {activeTab === 'family' && (
          <FamilyViewScreen
            currentPhase={currentPhase}
            userRole={settings.role}
            todayTips={todayTips}
            onRoleChange={handleRoleChange}
          />
        )}

        {activeTab === 'reminders' && <RemindersScreen />}
        {activeTab === 'evidence' && <EvidenceScreen />}
        {activeTab === 'doctor' && <DoctorVisitCardScreen cycles={cycles} messages={messages} />}
        {activeTab === 'voice' && <VoiceLoggingScreen onSaved={loadAll} />}
        {activeTab === 'year' && <YearInCyclesScreen cycles={cycles} />}
      </main>

      {/* Bottom Navigation */}
      <BottomNav
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onQuickHideDisguise={() => setIsDisguised(true)}
      />
    </div>
  );
};
