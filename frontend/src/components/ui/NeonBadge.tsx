import React from 'react';
import { cn } from '@/lib/utils';

type BadgeColor = 'cyan' | 'blue' | 'green' | 'yellow' | 'red' | 'dim';

interface NeonBadgeProps {
  label: string;
  color?: BadgeColor;
  pulse?: boolean;
  className?: string;
}

const COLOR_CLASSES: Record<BadgeColor, string> = {
  cyan:   'border-jarvis-cyan text-jarvis-cyan',
  blue:   'border-jarvis-blue text-jarvis-blue',
  green:  'border-jarvis-green text-jarvis-green',
  yellow: 'border-jarvis-yellow text-jarvis-yellow',
  red:    'border-jarvis-red text-jarvis-red',
  dim:    'border-jarvis-border text-jarvis-text-dim',
};

export function NeonBadge({ label, color = 'cyan', pulse = false, className }: NeonBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-mono font-medium uppercase tracking-wider',
        COLOR_CLASSES[color],
        className,
      )}
    >
      {pulse && (
        <span
          className={cn(
            'w-1 h-1 rounded-full animate-pulse',
            color === 'green' ? 'bg-jarvis-green' : color === 'red' ? 'bg-jarvis-red' : 'bg-jarvis-cyan',
          )}
        />
      )}
      {label}
    </span>
  );
}
