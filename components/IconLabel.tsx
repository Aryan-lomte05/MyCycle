import React from 'react';

interface IconLabelProps {
  icon: React.ReactNode;
  label: string;
  sublabel?: string;
  className?: string;
}

export const IconLabel: React.FC<IconLabelProps> = ({ icon, label, sublabel, className = '' }) => {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <div className="flex items-center justify-center p-2.5 rounded-xl bg-teal-100 text-teal-800 shrink-0">
        {icon}
      </div>
      <div>
        <div className="font-semibold text-slate-800 text-sm sm:text-base leading-tight">{label}</div>
        {sublabel && <div className="text-xs text-slate-500 mt-0.5">{sublabel}</div>}
      </div>
    </div>
  );
};
