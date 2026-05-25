import { m } from 'framer-motion';
import { cn } from '@/lib/utils';

export type Status =
  | 'ok'
  | 'warn'
  | 'error'
  | 'idle'
  | 'loading'
  | 'online'
  | 'offline'
  | 'warning'
  | 'degraded'
  | 'active'
  | 'inactive';

interface StatusDotProps {
  status: Status;
  label?: string;
  className?: string;
  showRing?: boolean;
}

const DOT_CLASSES: Record<Status, string> = {
  ok:      'bg-jarvis-green',
  online:  'bg-jarvis-green',
  active:  'bg-jarvis-green',
  warn:     'bg-jarvis-yellow',
  warning:  'bg-jarvis-yellow',
  degraded: 'bg-jarvis-yellow',
  error:   'bg-jarvis-red',
  offline: 'bg-jarvis-red',
  inactive: 'bg-jarvis-text-dim',
  idle:    'bg-jarvis-text-dim',
  loading: 'bg-jarvis-cyan',
};

const PULSE_CLASSES: Record<Status, boolean> = {
  ok: true,
  online: true,
  active: true,
  warn: false,
  warning: false,
  degraded: false,
  error: true,
  offline: false,
  inactive: false,
  idle: false,
  loading: true,
};

export function StatusDot({ status, label, className, showRing = true }: StatusDotProps) {
  const shouldPulse = PULSE_CLASSES[status];

  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span className="relative inline-flex">
        <span
          className={cn(
            'inline-block w-2 h-2 rounded-full flex-shrink-0',
            DOT_CLASSES[status],
            shouldPulse && 'animate-pulse',
          )}
        />
        {showRing && shouldPulse && (
          <m.span
            className={cn(
              'absolute inset-0 w-2 h-2 rounded-full',
              DOT_CLASSES[status],
            )}
            animate={{ scale: [1, 2, 1], opacity: [0.4, 0, 0.4] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
          />
        )}
      </span>
      {label && <span className="text-xs font-mono text-jarvis-text-dim">{label}</span>}
    </span>
  );
}
