import React from 'react';
import { cn } from '@/lib/utils';

type Status = 'ok' | 'warn' | 'error' | 'idle' | 'loading';

interface StatusDotProps {
  status: Status;
  className?: string;
}

const DOT_CLASSES: Record<Status, string> = {
  ok:      'bg-jarvis-green animate-pulse',
  warn:    'bg-jarvis-yellow',
  error:   'bg-jarvis-red animate-pulse',
  idle:    'bg-jarvis-text-dim',
  loading: 'bg-jarvis-cyan animate-pulse',
};

export function StatusDot({ status, className }: StatusDotProps) {
  return (
    <span
      className={cn('inline-block w-2 h-2 rounded-full flex-shrink-0', DOT_CLASSES[status], className)}
    />
  );
}
