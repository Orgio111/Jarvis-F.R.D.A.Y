import React from 'react';
import { m } from 'framer-motion';
import { cn } from '@/lib/utils';

interface CockpitButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: React.ReactNode;
}

const VARIANT_CLASSES = {
  default: 'border-jarvis-border text-jarvis-text hover:border-jarvis-cyan hover:text-jarvis-cyan',
  primary: 'border-jarvis-cyan bg-jarvis-cyan text-jarvis-bg hover:shadow-neon-cyan',
  danger:  'border-jarvis-red text-jarvis-red hover:bg-jarvis-red hover:text-jarvis-bg',
  ghost:   'border-transparent text-jarvis-text-dim hover:text-jarvis-text',
};

const SIZE_CLASSES = {
  sm: 'px-3 py-1 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-6 py-3 text-base',
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
        'inline-flex items-center gap-2 rounded border font-medium transition-all duration-150 select-none',
        'disabled:opacity-40 disabled:cursor-not-allowed',
        VARIANT_CLASSES[variant],
        SIZE_CLASSES[size],
        className,
      )}
      whileTap={!disabled && !loading ? { scale: 0.97 } : undefined}
      disabled={disabled || loading}
      {...(rest as any)}
    >
      {loading ? (
        <span className="w-3 h-3 rounded-full border border-current border-t-transparent animate-spin" />
      ) : (
        icon
      )}
      {children}
    </m.button>
  );
}
