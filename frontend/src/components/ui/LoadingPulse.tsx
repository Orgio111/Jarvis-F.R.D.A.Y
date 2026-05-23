import { m } from 'framer-motion';
import { Loader2 } from 'lucide-react';

interface LoadingPulseProps {
  size?: 'sm' | 'md' | 'lg';
  label?: string;
}

const SIZES = { sm: 'w-6 h-6', md: 'w-10 h-10', lg: 'w-16 h-16' };

export function LoadingPulse({ size = 'md', label }: LoadingPulseProps) {
  return (
    <div className="flex flex-col items-center gap-4">
      <div className={`relative ${SIZES[size]}`}>
        {/* Outer ring */}
        <m.div
          className="absolute inset-0 rounded-full border border-jarvis-cyan/30"
          animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        />
        {/* Middle ring */}
        <m.div
          className="absolute inset-1 rounded-full border border-jarvis-cyan/50"
          animate={{ scale: [1, 1.3, 1], opacity: [0.6, 0.1, 0.6] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut', delay: 0.2 }}
        />
        {/* Inner spinner */}
        <m.div
          className="absolute inset-2 rounded-full border-t-2 border-jarvis-cyan/80"
          animate={{ rotate: 360 }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
        />
        {/* Center dot */}
        <div className="absolute inset-0 flex items-center justify-center">
          <Loader2 size={size === 'sm' ? 10 : size === 'md' ? 14 : 20} className="text-jarvis-cyan animate-spin" />
        </div>
      </div>
      {label && (
        <m.p
          className="text-jarvis-text-dim text-xs font-mono"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        >
          {label}
        </m.p>
      )}
    </div>
  );
}
