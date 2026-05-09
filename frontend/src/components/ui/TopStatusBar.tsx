import React from 'react';
import { motion } from 'framer-motion';
import { GpuMiniIndicator } from '@/features/gpu/GpuMiniIndicator';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

export function TopStatusBar() {
  const data = useBootstrapStore((s) => s.data);
  const systemStatus = data?.system.status ?? 'initializing';
  const version = data?.system.version ?? '0.1.0';

  const statusColor =
    systemStatus === 'healthy' ? 'text-jarvis-green' :
    systemStatus === 'degraded' ? 'text-jarvis-yellow' :
    'text-jarvis-text-dim';

  const now = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });

  return (
    <div
      className="h-10 flex items-center justify-between px-4 border-b"
      style={{ borderColor: 'var(--jarvis-border)', background: 'rgba(8,12,20,0.95)' }}
    >
      {/* Left: JARVIS brand + system status */}
      <div className="flex items-center gap-3">
        <span className="text-jarvis-cyan text-sm font-bold tracking-[0.2em] neon-cyan">
          JARVIS
        </span>
        <span className="text-jarvis-border text-xs">|</span>
        <span className={`text-xs font-mono ${statusColor}`}>
          {systemStatus.toUpperCase()}
        </span>
        <span className="text-jarvis-text-dim text-xs font-mono">v{version}</span>
      </div>

      {/* Center: Provider / model info */}
      {data && (
        <div className="flex items-center gap-3">
          <ProviderChip
            label={data.providers.primary.name}
            status={data.providers.primary.status}
          />
          {data.providers.primary.status !== 'available' &&
            data.providers.fallback.status === 'available' && (
              <ProviderChip
                label={data.providers.fallback.name}
                status="available"
                isFallback
              />
            )}
        </div>
      )}

      {/* Right: GPU indicator + clock */}
      <div className="flex items-center gap-3">
        <GpuMiniIndicator />
        <Clock />
      </div>
    </div>
  );
}

function ProviderChip({
  label,
  status,
  isFallback,
}: {
  label: string;
  status: string;
  isFallback?: boolean;
}) {
  const available = status === 'available';
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          available ? 'bg-jarvis-green animate-pulse' : 'bg-jarvis-text-dim'
        }`}
      />
      <span className="text-xs font-mono text-jarvis-text-dim">
        {label}
        {isFallback && <span className="text-jarvis-yellow ml-1">[fb]</span>}
      </span>
    </div>
  );
}

function Clock() {
  const [time, setTime] = React.useState(
    new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
  );

  React.useEffect(() => {
    const id = setInterval(() => {
      setTime(
        new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
      );
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return <span className="text-xs font-mono text-jarvis-text-dim">{time}</span>;
}
