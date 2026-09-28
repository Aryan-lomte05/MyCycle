'use client';

import React from 'react';
import { Globe } from 'lucide-react';

interface LanguageSwitcherProps {
  currentLang: 'en' | 'hi' | 'mr';
  onSelect: (lang: 'en' | 'hi' | 'mr') => void;
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ currentLang, onSelect }) => {
  const options: { code: 'en' | 'hi' | 'mr'; label: string }[] = [
    { code: 'en', label: 'English' },
    { code: 'hi', label: 'हिंदी' },
    { code: 'mr', label: 'मराठी' },
  ];

  return (
    <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl border border-slate-200" role="group" aria-label="Language options">
      <Globe className="w-4 h-4 text-slate-500 ml-1.5 mr-0.5" />
      {options.map((opt) => (
        <button
          key={opt.code}
          onClick={() => onSelect(opt.code)}
          className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all min-h-[38px] ${
            currentLang === opt.code
              ? 'bg-teal-700 text-white shadow-xs'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200'
          }`}
          aria-pressed={currentLang === opt.code}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
};
