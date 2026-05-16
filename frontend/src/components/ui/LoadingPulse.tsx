import { m } from 'framer-motion';

interface LoadingPulseProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const SIZES = { sm: 'w-6 h-6', md: 'w-10 h-10', lg: 'w-16 h-16' };

export function LoadingPulse({ size = 'md', label }: LoadingPulseProps) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className={`relative ${SIZES[size]}`}>
        <m.div
          className="absolute inset-0 rounded-full border border-jarvis-cyan"
          animate={{ scale: [1, 1.5, 1], opacity: [1, 0, 1] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        />
        <m.div
          className="absolute inset-1 rounded-full border border-jarvis-cyan opacity-60"
          animate={{ scale: [1, 1.3, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.3 }}
        />
      </div>
      {label && (
        <p className="text-jarvis-text-dim text-xs font-mono animate-pulse">{label}</p>
      )}
    </div>
  );
}
