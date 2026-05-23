import React from 'react';
import { m } from 'framer-motion';
import { cn } from '@/lib/utils';

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  glow?: boolean;
  onClick?: () => void;
}

export function GlassPanel({ children, className, hover = false, glow = false, onClick }: GlassPanelProps) {
  return (
    <m.div
      className={cn(
        'relative',
        glow ? 'jarvis-panel-glow' : 'jarvis-panel',
        hover && 'jarvis-panel-hover cursor-pointer',
        className,
      )}
      onClick={onClick}
      whileHover={hover ? {
        scale: 1.005,
        y: -1,
        transition: { type: 'spring', stiffness: 300, damping: 25 },
      } : undefined}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      {/* Subtle top shine */}
      <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-jarvis-cyan/20 to-transparent pointer-events-none" />

      {children}
    </m.div>
  );
}
