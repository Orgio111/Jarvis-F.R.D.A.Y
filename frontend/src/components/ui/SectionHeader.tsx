import React from 'react';
import { cn } from '@/lib/utils';

interface SectionHeaderProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  className?: string;
}

export function SectionHeader({ title, subtitle, action, className }: SectionHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between mb-3', className)}>
      <div>
        <h3 className="text-jarvis-text-bright text-sm font-semibold tracking-wide uppercase">
          {title}
        </h3>
        {subtitle && (
          <p className="text-jarvis-text-dim text-xs mt-0.5">{subtitle}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
