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
        'relative group',
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
      whileTap={hover ? {
        scale: 0.995,
        transition: { type: 'spring', stiffness: 400, damping: 20 },
      } : undefined}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
    >
      {/* Default subtle top shine */}
      <div className="absolute top-0 left-1/4 right-1/4 h-px bg-gradient-to-r from-transparent via-jarvis-cyan/20 to-transparent pointer-events-none" />

      {/* Hover border glow overlay — only visible when hover is enabled */}
      {hover && (
        <>
          {/* Corner accent glow */}
          <div className="absolute -top-px -left-px w-12 h-12 rounded-tl-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
            style={{
              background: 'linear-gradient(135deg, rgba(0,212,255,0.12) 0%, transparent 70%)',
            }}
          />
          <div className="absolute -bottom-px -right-px w-12 h-12 rounded-br-lg opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
            style={{
              background: 'linear-gradient(315deg, rgba(0,212,255,0.08) 0%, transparent 70%)',
            }}
          />

          {/* Moving shine line */}
          <m.div
            className="absolute top-0 h-px opacity-0 group-hover:opacity-100 pointer-events-none"
            style={{
              left: '-10%',
              width: '40%',
              background: 'linear-gradient(90deg, transparent, rgba(0,212,255,0.35), transparent)',
            }}
            animate={{
              left: ['-10%', '110%'],
            }}
            transition={{
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
              repeatDelay: 1,
            }}
          />

          {/* Shadow depth increase on hover */}
          <div className="absolute inset-0 rounded-[inherit] opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
            style={{
              boxShadow: 'inset 0 0 30px rgba(0,212,255,0.03), 0 8px 40px rgba(0,0,0,0.3)',
            }}
          />
        </>
      )}

      {children}
    </m.div>
  );
}
