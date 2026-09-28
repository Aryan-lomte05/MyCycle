import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'simulated' | 'normal' | 'amber' | 'neutral';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral', className = '' }) => {
  const styles = {
    simulated: 'bg-amber-100 text-amber-900 border border-amber-300 font-medium shadow-xs',
    normal: 'bg-teal-100 text-teal-900 border border-teal-300 font-medium',
    amber: 'bg-amber-50 text-amber-800 border border-amber-200 font-medium',
    neutral: 'bg-slate-100 text-slate-800 border border-slate-300 font-medium',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold tracking-wide ${styles[variant]} ${className}`}
      role="status"
    >
      {variant === 'simulated' && <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />}
      {children}
    </span>
  );
};

export const SimulatedBadge: React.FC<{ label?: string }> = ({ label = 'Simulated demo data' }) => {
  return <Badge variant="simulated">{label}</Badge>;
};
