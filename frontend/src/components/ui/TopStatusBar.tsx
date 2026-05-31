import { useState, useEffect } from 'react';
import { m } from 'framer-motion';
import { Clock as ClockIcon, HardDrive } from 'lucide-react';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

export function TopStatusBar() {
  const data = useBootstrapStore((s) => s.data);
  const systemStatus = data?.system.status ?? 'initializing';
  const version = data?.system.version ?? '0.1.0';

  const statusColor =
    systemStatus === 'healthy' ? 'text-jarvis-green' :
    systemStatus === 'degraded' ? 'text-jarvis-yellow' :
    'text-jarvis-text-dim';

  const statusDotColor =
    systemStatus === 'healthy' ? 'bg-jarvis-green' :
    systemStatus === 'degraded' ? 'bg-jarvis-yellow' :
    'bg-jarvis-text-dim';

  return (
    <header
      className="relative h-[68px] flex items-center justify-between px-5 sm:px-5 pl-12 sm:pl-5 border-b bg-jarvis-bg/95 backdrop-blur-md shrink-0"
      style={{ borderColor: 'var(--jarvis-border)' }}
    >
      {/* Animated gradient bottom border */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-jarvis-cyan/40 via-jarvis-blue/30 to-transparent" />

      {/* ── Left: J.A.R.V.I.S brand ── */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-3">
          <m.span
            className="text-jarvis-cyan text-xl font-bold tracking-[0.15em] neon-cyan font-sans jarvis-flicker"
            animate={{ textShadow: [
              '0 0 8px rgba(0,229,255,0.4)',
              '0 0 20px rgba(0,229,255,0.9)',
              '0 0 8px rgba(0,229,255,0.4)',
            ]}}
            transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          >
            J.A.R.V.I.S
          </m.span>

          {/* Status indicator */}
          <div className="flex items-center gap-2 px-3 py-1 rounded-full border border-jarvis-border/30 bg-jarvis-bg-2/50">
            <span className="relative flex items-center justify-center w-2.5 h-2.5">
              <span className={`w-1.5 h-1.5 rounded-full ${statusDotColor} relative`} />
              {systemStatus === 'healthy' && (
                <m.span
                  className="absolute inset-0 rounded-full bg-jarvis-green"
                  animate={{ scale: [1, 2.5, 1], opacity: [0.4, 0, 0.4] }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
                />
              )}
            </span>
            <span className={`text-[11px] font-mono ${statusColor} uppercase tracking-widest font-semibold`}>
              {systemStatus === 'healthy' ? 'ONLINE' : systemStatus}
            </span>
          </div>
        </div>
      </div>

      {/* ── Center: Provider / model info ── */}
      {data && (
        <div className="hidden md:flex items-center gap-3">
          <Chip
            label={data.providers.primary.name}
            status={data.providers.primary.status}
          />
          {data.providers.primary.status !== 'available' &&
            data.providers.fallback.status === 'available' && (
              <Chip
                label={data.providers.fallback.name}
                status="available"
                isFallback
              />
            )}
        </div>
      )}

      {/* ── Right: GPU + clock ── */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-jarvis-border/30 bg-jarvis-bg-2/50">
          <HardDrive size={12} className="text-jarvis-text-dim/40" />
          <Clock />
          <span className="text-jarvis-text-dim/40 text-[10px] font-mono hidden sm:inline">v{version}</span>
        </div>
      </div>
    </header>
  );
}

// ─── Provider Chip ──────────────────────────────────────────────────────────

function Chip({
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
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-jarvis-border/20 bg-jarvis-bg-2/40">
      <span className="relative flex items-center justify-center w-1.5 h-1.5">
        <span className={`w-1.5 h-1.5 rounded-full ${available ? 'bg-jarvis-green' : 'bg-jarvis-text-dim'}`} />
        {available && (
          <m.span
            className="absolute inset-0 rounded-full bg-jarvis-green"
            animate={{ scale: [1, 2], opacity: [0.3, 0] }}
            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeOut' }}
          />
        )}
      </span>
      <span className="text-xs font-mono text-jarvis-text-dim/70">
        {label}
        {isFallback && <span className="text-jarvis-yellow ml-1 text-[10px]">[fb]</span>}
      </span>
    </div>
  );
}

// ─── Clock ──────────────────────────────────────────────────────────────────

function Clock() {
  const [time, setTime] = useState(
    new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
  );
  const [date, setDate] = useState(
    new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
  );

  useEffect(() => {
    const id = setInterval(() => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }),
      );
      setDate(
        now.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      );
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="flex items-center gap-2">
      <ClockIcon size={10} className="text-jarvis-text-dim/30" />
      <span className="text-xs font-mono text-jarvis-text-dim/60">{time}</span>
      <span className="text-[10px] font-mono text-jarvis-text-dim/30 hidden sm:inline">{date}</span>
    </div>
  );
}
