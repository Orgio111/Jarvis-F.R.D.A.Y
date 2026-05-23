import React from 'react';
import { m } from 'framer-motion';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

interface CockpitButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'danger' | 'ghost' | 'glow';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

const VARIANT_CLASSES = {
  default: 'border-jarvis-border/30 text-jarvis-text hover:border-jarvis-cyan/40 hover:text-jarvis-cyan hover:bg-jarvis-cyan/5',
  primary: 'border-jarvis-cyan bg-jarvis-cyan text-jarvis-bg hover:shadow-[0_0_20px_rgba(0,212,255,0.4)] hover:brightness-110',
  danger:  'border-jarvis-red/40 text-jarvis-red hover:bg-jarvis-red/10 hover:border-jarvis-red/60',
  ghost:   'border-transparent text-jarvis-text-dim hover:text-jarvis-text hover:bg-jarvis-bg-2/50',
  glow:    'border-jarvis-cyan/30 text-jarvis-cyan bg-jarvis-cyan/5 hover:bg-jarvis-cyan/10 hover:border-jarvis-cyan/50 hover:shadow-[0_0_20px_rgba(0,212,255,0.15)]',
};

const SIZE_CLASSES = {
  sm: 'px-3 py-1.5 text-xs rounded-lg',
  md: 'px-4 py-2 text-sm rounded-xl',
  lg: 'px-6 py-3 text-base rounded-xl',
};

export function CockpitButton({
  variant = 'default',
  size = 'md',
  loading = false,
  icon,
  className,
  children,
  disabled,
  ...rest
}: CockpitButtonProps) {
  return (
    <m.button
      className={cn(
        'inline-flex items-center gap-2 border font-medium transition-all duration-200 select-none',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      whileTap={!disabled && !loading ? { scale: 0.97 } : undefined}
      whileHover={!disabled && !loading ? { y: -1 } : undefined}
      disabled={disabled || loading}
      {...(rest as any)}
    >
      {loading ? (
        <Loader2 size={14} className="animate-spin" />
      ) : (
        icon
      )}
      {children}
    </m.button>
  );
}
