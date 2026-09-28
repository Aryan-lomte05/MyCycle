import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
  variant?: 'default' | 'amber' | 'teal' | 'flat';
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({ children, className = '', variant = 'default', onClick }) => {
  const variants = {
    default: 'bg-white border border-slate-200 shadow-xs text-slate-900',
    amber: 'bg-amber-50/70 border border-amber-300 shadow-xs text-amber-950',
    teal: 'bg-teal-50/70 border border-teal-200 shadow-xs text-teal-950',
    flat: 'bg-slate-50 border border-slate-200 text-slate-900',
  };

  return (
    <div
      onClick={onClick}
      className={`rounded-2xl p-4 sm:p-5 transition-all ${variants[variant]} ${
        onClick ? 'cursor-pointer hover:shadow-md active:scale-[0.99]' : ''
      } ${className}`}
    >
      {children}
    </div>
  );
};
