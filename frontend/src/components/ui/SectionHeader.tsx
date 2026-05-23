import React from 'react';
import { cn } from '@/lib/utils';

interface SectionHeaderProps {
  title: React.ReactNode;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}

export function SectionHeader({ title, subtitle, action, className }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between mb-4', className)}>
      <div className="space-y-0.5">
        <h3 className="text-jarvis-text-bright text-xs font-mono font-semibold tracking-wider uppercase">
          {title}
        </h3>
        {subtitle && (
          <p className="text-jarvis-text-dim text-[10px] font-mono opacity-70">{subtitle}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
