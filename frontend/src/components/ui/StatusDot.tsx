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
  | 'degraded';

interface StatusDotProps {
  status: Status;
  label?: string;
  className?: string;
}

const DOT_CLASSES: Record<Status, string> = {
  ok:      'bg-jarvis-green animate-pulse',
  online:  'bg-jarvis-green animate-pulse',
  warn:     'bg-jarvis-yellow',
  warning:  'bg-jarvis-yellow',
  degraded: 'bg-jarvis-yellow',
  error:   'bg-jarvis-red animate-pulse',
  offline: 'bg-jarvis-red',
  idle:    'bg-jarvis-text-dim',
  loading: 'bg-jarvis-cyan animate-pulse',
};

export function StatusDot({ status, label, className }: StatusDotProps) {
  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span
        className={cn('inline-block w-2 h-2 rounded-full flex-shrink-0', DOT_CLASSES[status])}
      />
      {label && <span className="text-xs font-mono text-jarvis-text-dim">{label}</span>}
    </span>
  );
}
