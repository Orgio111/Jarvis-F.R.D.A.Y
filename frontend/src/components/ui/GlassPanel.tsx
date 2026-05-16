import React from 'react';
import { m } from 'framer-motion';
import { cn } from '@/lib/utils';

interface GlassPanelProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
}

export function GlassPanel({ children, className, hover = false, onClick }: GlassPanelProps) {
  return (
    <m.div
      className={cn(
        'jarvis-panel',
        hover && 'jarvis-panel-hover cursor-pointer',
        className,
      )}
      onClick={onClick}
      whileHover={hover ? { scale: 1.005 } : undefined}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {children}
    </m.div>
  );
}
