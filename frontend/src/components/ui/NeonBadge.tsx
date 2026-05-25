import { m } from 'framer-motion';
import { cn } from '@/lib/utils';

type BadgeColor = 'cyan' | 'blue' | 'green' | 'yellow' | 'red' | 'purple' | 'dim';

interface NeonBadgeProps {
  label?: string;
  children?: React.ReactNode;
  color?: BadgeColor;
  pulse?: boolean;
  size?: 'sm' | 'md';
  className?: string;
}

const COLOR_CLASSES: Record<BadgeColor, string> = {
  cyan:   'border-jarvis-cyan/30 text-jarvis-cyan bg-jarvis-cyan/5',
  blue:   'border-jarvis-blue/30 text-jarvis-blue bg-jarvis-blue/5',
  green:  'border-jarvis-green/30 text-jarvis-green bg-jarvis-green/5',
  yellow: 'border-jarvis-yellow/30 text-jarvis-yellow bg-jarvis-yellow/5',
  red:    'border-jarvis-red/30 text-jarvis-red bg-jarvis-red/5',
  purple: 'border-jarvis-purple/30 text-jarvis-purple bg-jarvis-purple/5',
  dim:    'border-jarvis-border/30 text-jarvis-text-dim bg-jarvis-bg-2/50',
};

const SIZE_CLASSES = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2.5 py-1 text-xs',
};

export function NeonBadge({ label, children, color = 'cyan', pulse = false, size = 'md', className }: NeonBadgeProps) {
  const dotColor = color === 'green' ? 'bg-jarvis-green' :
                   color === 'red' ? 'bg-jarvis-red' :
                   color === 'yellow' ? 'bg-jarvis-yellow' :
                   color === 'blue' ? 'bg-jarvis-blue' :
                   color === 'purple' ? 'bg-jarvis-purple' :
                   color === 'dim' ? 'bg-jarvis-text-dim' :
                   'bg-jarvis-cyan';

  const borderGlow = color === 'green' ? 'shadow-[0_0_10px_rgba(0,255,136,0.15)] group-hover:shadow-[0_0_18px_rgba(0,255,136,0.25)]' :
                     color === 'cyan' ? 'shadow-[0_0_10px_rgba(0,212,255,0.15)] group-hover:shadow-[0_0_18px_rgba(0,212,255,0.25)]' :
                     color === 'red' ? 'shadow-[0_0_10px_rgba(255,68,102,0.15)] group-hover:shadow-[0_0_18px_rgba(255,68,102,0.25)]' :
                     '';

  return (
    <m.span
      className={cn(
        'group inline-flex items-center gap-1.5 rounded-full border font-mono font-medium uppercase tracking-wider',
        'transition-all duration-300 ease-out',
        borderGlow,
        COLOR_CLASSES[color],
        SIZE_CLASSES[size],
        className,
      )}
      whileHover={{
        scale: 1.04,
        transition: { type: 'spring', stiffness: 400, damping: 15, mass: 0.5 },
      }}
      whileTap={{ scale: 0.95 }}
    >
      {pulse && (
        <span className={`w-1.5 h-1.5 rounded-full ${dotColor} ${pulse ? 'animate-pulse' : ''}`} />
      )}
      {children ?? label}
    </m.span>
  );
}
