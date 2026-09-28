'use client';

import React from 'react';
import { Home, PlusCircle, BarChart2, Shield, Users, EyeOff } from 'lucide-react';

interface BottomNavProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  onQuickHideDisguise?: () => void;
}

export const BottomNav: React.FC<BottomNavProps> = ({ activeTab, onTabChange, onQuickHideDisguise }) => {
  const tabs = [
    { id: 'home', label: 'Home', icon: Home },
    { id: 'log', label: 'Log Cycle', icon: PlusCircle },
    { id: 'baseline', label: 'Baseline', icon: BarChart2 },
    { id: 'privacy', label: 'Privacy', icon: Shield },
    { id: 'family', label: 'Circle', icon: Users },
  ];

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 max-w-md mx-auto bg-white/95 backdrop-blur-md border-t border-slate-200 px-2 py-2 flex items-center justify-around z-40 shadow-lg"
      aria-label="Main Navigation"
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;

        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex flex-col items-center justify-center py-1 px-2 rounded-xl transition-all min-h-[44px] min-w-[48px] ${
              isActive ? 'text-teal-700 font-bold bg-teal-50' : 'text-slate-500 hover:text-slate-800'
            }`}
            aria-current={isActive ? 'page' : undefined}
          >
            <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.5]' : 'stroke-2'}`} />
            <span className="text-[10px] tracking-tight mt-0.5">{tab.label}</span>
          </button>
        );
      })}

      {onQuickHideDisguise && (
        <button
          onClick={onQuickHideDisguise}
          className="flex flex-col items-center justify-center py-1 px-2 rounded-xl text-amber-700 hover:bg-amber-50 min-h-[44px] min-w-[44px]"
          title="Quick Hide (Disguise Mode)"
          aria-label="Quick hide app with calculator disguise"
        >
          <EyeOff className="w-5 h-5 stroke-[2]" />
          <span className="text-[10px] tracking-tight mt-0.5">Hide</span>
        </button>
      )}
    </nav>
  );
};
