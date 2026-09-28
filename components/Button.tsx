import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'amber' | 'outline' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  className = '',
  ...props
}) => {
  const base =
    'inline-flex items-center justify-center font-medium rounded-xl transition-all focus:outline-hidden focus:ring-2 focus:ring-offset-2 active:scale-98 disabled:opacity-50 disabled:pointer-events-none min-h-[44px] min-w-[44px] touch-manipulation select-none';

  const variants = {
    primary: 'bg-teal-700 hover:bg-teal-800 text-white focus:ring-teal-600 shadow-sm',
    secondary: 'bg-teal-100 hover:bg-teal-200 text-teal-900 focus:ring-teal-500',
    amber: 'bg-amber-600 hover:bg-amber-700 text-white focus:ring-amber-500 shadow-sm',
    outline: 'border-2 border-slate-300 hover:bg-slate-50 text-slate-800 focus:ring-slate-400',
    danger: 'bg-rose-600 hover:bg-rose-700 text-white focus:ring-rose-500',
  };

  const sizes = {
    sm: 'text-xs px-3 py-2',
    md: 'text-sm px-4 py-2.5',
    lg: 'text-base px-6 py-3',
  };

  return (
    <button
      className={`${base} ${variants[variant]} ${sizes[size]} ${fullWidth ? 'w-full' : ''} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};
