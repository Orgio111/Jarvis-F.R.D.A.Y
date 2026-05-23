import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { m } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import {
  Activity,
  Cpu,
  MessageSquare,
  Search,
  Database,
  BarChart3,
  Zap,
  CircuitBoard,
  HardDrive,
  AlertTriangle,
  Server,
  Eye,
  Mic,
  Wrench,
  PlayCircle,
  Terminal,
  Boxes,
  RefreshCw,
  Shield,
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { HudVisualization } from '@/components/ui/HudVisualization';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { useGpuStore } from '@/features/gpu/gpuStore';
import type { HealthResponse, FeatureFlags } from '@/lib/api/types';

// ─── Animated Counter ────────────────────────────────────────────────────────

function AnimatedCounter({ value, suffix = '', decimals = 0 }: { value: number; suffix?: string; decimals?: number }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 800;
    const steps = 20;
    const increment = value / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(current);
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [value]);

  return (
    <span className="metric-value text-jarvis-text-bright">
      {displayValue.toFixed(decimals)}{suffix}
    </span>
  );
}

// ─── Pass/Fail indicator ────────────────────────────────────────────────────

function PassFail({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 group cursor-default">
      <m.div
        className={`w-2 h-2 rounded-full ${ok ? 'bg-jarvis-green' : 'bg-jarvis-red'}`}
        animate={ok ? { scale: [1, 1.2, 1] } : undefined}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      />
      <span className="text-xs font-mono text-jarvis-text-dim group-hover:text-jarvis-text transition-colors duration-200">{label}</span>
    </div>
  );
}

// ─── Utilization Bar ─────────────────────────────────────────────────────────

function UtilizationBar({ label, pct, color, barColor }: { label: string; pct: number; color: string; barColor: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs font-mono">
        <span className="text-jarvis-text-dim/80">{label}</span>
        <span className={color}>{Math.round(pct)}%</span>
      </div>
      <div className="h-1.5 bg-jarvis-bg-3/50 rounded-full overflow-hidden">
        <m.div
          className={`h-full rounded-full ${barColor}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

// ─── Feature pill grid ────────────────────────────────────────────────────────

const FEATURE_LABELS: Record<keyof FeatureFlags, string> = {
  chat: 'Chat',
  voice: 'Voice',
  vision: 'Vision',
  memory: 'Memory',
  tools: 'Tools',
  execution: 'Execution',
  search: 'Search',
  terminal: 'Terminal',
  localControl: 'Local Actions',
  selfImprovement: 'Self-Improve',
  localLlm: 'Local LLM',
  gpuMonitor: 'GPU Monitor',
};

const FEATURE_ROUTES: Partial<Record<keyof FeatureFlags, string>> = {
  chat: '/chat',
  voice: '/voice',
  vision: '/vision',
  memory: '/memory',
  tools: '/tools',
  execution: '/execution',
  search: '/search',
  localControl: '/local-actions',
  selfImprovement: '/self-improvement',
  gpuMonitor: '/gpu',
};

const FEATURE_ICONS: Partial<Record<keyof FeatureFlags, React.ReactNode>> = {
  chat: <MessageSquare size={12} />,
  voice: <Mic size={12} />,
  vision: <Eye size={12} />,
  memory: <Database size={12} />,
  tools: <Wrench size={12} />,
  execution: <PlayCircle size={12} />,
  search: <Search size={12} />,
  terminal: <Terminal size={12} />,
  gpuMonitor: <Cpu size={12} />,
  localControl: <Zap size={12} />,
  selfImprovement: <RefreshCw size={12} />,
};

function FeaturePill({ name, enabled, route, icon }: { name: string; enabled: boolean; route?: string; icon?: React.ReactNode }) {
  const cls = [
    'inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono border transition-all duration-200',
    enabled
      ? 'border-jarvis-cyan/25 text-jarvis-cyan bg-jarvis-cyan/[0.04] hover:bg-jarvis-cyan/10 hover:border-jarvis-cyan/40 hover:shadow-[0_0_12px_rgba(0,212,255,0.1)] cursor-pointer'
      : 'border-jarvis-border/30 text-jarvis-text-dim/40 opacity-40 cursor-default',
  ].join(' ');

  if (enabled && route) {
    return <Link to={route} className={cls}>{icon}{name}</Link>;
  }
  return <span className={cls}>{name}</span>;
}

// ─── Quick Action Button ─────────────────────────────────────────────────────

function QuickActionButton({ to, icon, label, color }: { to: string; icon: React.ReactNode; label: string; color: string }) {
  return (
    <Link
      to={to}
      className="group flex items-center gap-2.5 p-2.5 rounded-lg border border-jarvis-border/20 bg-jarvis-bg-2/30 transition-all duration-200 hover:border-jarvis-cyan/30 cursor-pointer"
    >
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-200 group-hover:scale-110"
        style={{ color, background: `color-mix(in srgb, ${color} 10%, transparent)` }}
      >
        {icon}
      </div>
      <span className="text-xs font-mono text-jarvis-text-dim group-hover:text-jarvis-text transition-colors duration-200">{label}</span>
    </Link>
  );
}

// ─── Tab Button ──────────────────────────────────────────────────────────────

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'diagnostics', label: 'Diagnostics' },
  { key: 'network', label: 'Network' },
  { key: 'security', label: 'Security' },
  { key: 'aicore', label: 'AI Core' },
];

// ─── HUD Frame ───────────────────────────────────────────────────────────────

function HudFrame({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`jarvis-panel relative overflow-hidden ${className}`}>
      {/* Corner brackets */}
      <svg className="absolute top-0 left-0 w-4 h-4 pointer-events-none" viewBox="0 0 16 16">
        <path d="M1,5 L1,1 L5,1" fill="none" stroke="rgba(0,229,255,0.4)" strokeWidth="1" />
      </svg>
      <svg className="absolute top-0 right-0 w-4 h-4 pointer-events-none" viewBox="0 0 16 16">
        <path d="M11,1 L15,1 L15,5" fill="none" stroke="rgba(0,229,255,0.4)" strokeWidth="1" />
      </svg>
      <svg className="absolute bottom-0 left-0 w-4 h-4 pointer-events-none" viewBox="0 0 16 16">
        <path d="M1,11 L1,15 L5,15" fill="none" stroke="rgba(0,229,255,0.4)" strokeWidth="1" />
      </svg>
      <svg className="absolute bottom-0 right-0 w-4 h-4 pointer-events-none" viewBox="0 0 16 16">
        <path d="M11,15 L15,15 L15,11" fill="none" stroke="rgba(0,229,255,0.4)" strokeWidth="1" />
      </svg>
      {children}
    </div>
  );
}

// ─── DASHBOARD ───────────────────────────────────────────────────────────────

export function DashboardPage() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const bootstrap = useBootstrapStore((s) => s.data);
  const gpuStatus = useGpuStore((s) => s.status);
  const [activeTab, setActiveTab] = useState('overview');

  const { data: health } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => apiClient.get<HealthResponse>('/health'),
    enabled: bootstrapReady,
    staleTime: 20_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
  });

  const sys = bootstrap?.system;
  const providers = bootstrap?.providers;
  const gpu = bootstrap?.gpu;
  const features = bootstrap?.features;

  const checks = health?.checks ?? {};
  const pythonOk = checks['python-ai-service']?.status === 'pass';
  const redisOk = checks['redis']?.status === 'pass';
  const brokerOk = checks['rust-broker']?.status === 'pass';
  const gatewayOk = checks['gateway']?.status === 'pass';
  const allServicesOk = pythonOk && redisOk && brokerOk;

  const activeProviderCount = providers?.available?.length ?? 0;

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {/* ── Page Header ── */}
      <m.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-jarvis-text-bright text-lg font-semibold tracking-wide flex items-center gap-3">
            <span className="text-jarvis-cyan neon-cyan">COMMAND CENTER</span>
          </h1>
          <p className="text-jarvis-text-dim text-xs font-mono mt-0.5 tracking-wider">
            {sys ? `v${sys.version} · ${sys.appEnv}` : 'AI Operating System'}
          </p>
        </div>
        <NeonBadge
          color={allServicesOk ? 'green' : sys?.status === 'degraded' ? 'yellow' : 'red'}
          label={allServicesOk ? 'ALL SYSTEMS OPERATIONAL' : sys?.status ?? 'Unknown'}
          pulse={allServicesOk}
        />
      </m.div>

      {/* ── HUD Center Row ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Left: System Diagnostics */}
        <HudFrame className="p-5 lg:col-span-2">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={14} className="text-jarvis-cyan" />
            <span className="text-jarvis-cyan text-xs font-mono font-bold tracking-[0.15em] uppercase">SYSTEM DIAGNOSTICS</span>
          </div>

          {sys ? (
            <div className="space-y-3">
              {/* Main status */}
              <div className="flex items-center gap-3 p-3 rounded-lg bg-jarvis-bg-2/60 border border-jarvis-border/30">
                <m.div
                  className={`w-3 h-3 rounded-full ${sys.status === 'healthy' ? 'bg-jarvis-green' : sys.status === 'degraded' ? 'bg-jarvis-yellow' : 'bg-jarvis-red'}`}
                  animate={sys.status === 'healthy' ? { scale: [1, 1.3, 1], opacity: [1, 0.6, 1] } : undefined}
                  transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                />
                <div>
                  <p className="text-jarvis-text-bright text-sm font-mono capitalize">{sys.status}</p>
                  <p className="text-jarvis-text-dim text-xs font-mono">{sys.appEnv} environment</p>
                </div>
              </div>

              {/* Power Level / Systems Online / Core Temp */}
              <div className="space-y-2.5">
                <div className="flex items-center justify-between py-1.5 border-b border-jarvis-border/10">
                  <span className="text-xs font-mono text-jarvis-text-dim/80">Power Level</span>
                  <span className="text-xs font-mono text-jarvis-green">100%</span>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-jarvis-border/10">
                  <span className="text-xs font-mono text-jarvis-text-dim/80">Systems Online</span>
                  <span className="text-xs font-mono text-jarvis-green">98%</span>
                </div>
                <div className="flex items-center justify-between py-1.5 border-b border-jarvis-border/10">
                  <span className="text-xs font-mono text-jarvis-text-dim/80">Core Temp</span>
                  <span className="text-xs font-mono text-jarvis-yellow">42°C</span>
                </div>
              </div>

              {/* Service checks */}
              <div className="grid grid-cols-2 gap-1.5 pt-1">
                <PassFail ok={pythonOk} label="AI Service" />
                <PassFail ok={redisOk} label="Redis" />
                <PassFail ok={brokerOk} label="Broker" />
                <PassFail ok={gatewayOk} label="Gateway" />
              </div>

              {health && (
                <div className="flex items-center justify-between pt-2 border-t border-jarvis-border/20">
                  <span className="text-[10px] font-mono text-jarvis-text-dim/60">Overall health</span>
                  <span className={`text-xs font-mono ${health.status === 'pass' ? 'text-jarvis-green' : 'text-jarvis-red'}`}>
                    {health.status}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="h-32 flex items-center justify-center">
              <div className="text-jarvis-text-dim text-xs font-mono animate-pulse">Loading system data…</div>
            </div>
          )}
        </HudFrame>

        {/* Center: HUD Arc Reactor */}
        <HudFrame className="lg:col-span-1 flex items-center justify-center py-6">
          <HudVisualization size={220} />
        </HudFrame>

        {/* Right: GPU Radar / Status */}
        <HudFrame className="p-5 lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Cpu size={14} className="text-jarvis-purple" />
              <span className="text-jarvis-purple text-xs font-mono font-bold tracking-[0.15em] uppercase">GPU COMPUTE</span>
            </div>
            {gpu && (
              <NeonBadge
                color={gpu.cudaAvailable ? 'green' : 'dim'}
                label={gpu.cudaAvailable ? 'CUDA' : 'CPU'}
                size="sm"
              />
            )}
          </div>

          {gpu ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-jarvis-bg-2/50 border border-jarvis-border/30">
                <div className="flex items-center gap-2">
                  <CircuitBoard size={14} className="text-jarvis-text-dim" />
                  <span className="text-xs font-mono text-jarvis-text-dim">Device</span>
                </div>
                <span className="text-xs font-mono text-jarvis-text-bright truncate ml-2">
                  {gpu.activeDevice || 'CPU Fallback'}
                </span>
              </div>

              {gpu.cudaAvailable && (
                <div className="space-y-2.5">
                  <UtilizationBar label="GPU" pct={gpuStatus?.utilization.gpuPercent ?? 0} color="text-jarvis-cyan" barColor="bg-jarvis-cyan" />
                  <UtilizationBar label="Memory" pct={(gpu.vram.usedMb / gpu.vram.totalMb) * 100} color="text-jarvis-blue" barColor="bg-jarvis-blue" />
                  <div className="flex justify-between text-[10px] font-mono text-jarvis-text-dim/60 pt-1 border-t border-jarvis-border/20">
                    <span>Temp: {gpuStatus?.utilization.temperatureC.toFixed(0) ?? '—'}°C</span>
                    <span>Power: {gpuStatus?.utilization.powerWatts.toFixed(0) ?? '—'}W</span>
                    <span>VRAM: {gpu.vram.usedMb > 1024 ? `${(gpu.vram.usedMb / 1024).toFixed(1)}G` : `${gpu.vram.usedMb.toFixed(0)}M`} / {gpu.vram.totalMb > 1024 ? `${(gpu.vram.totalMb / 1024).toFixed(1)}G` : `${gpu.vram.totalMb.toFixed(0)}M`}</span>
                  </div>
                </div>
              )}

              {!gpu.cudaAvailable && (
                <div className="p-3 rounded-lg bg-jarvis-yellow/5 border border-jarvis-yellow/20">
                  <p className="text-jarvis-yellow text-xs font-mono flex items-center gap-2">
                    <AlertTriangle size={12} />
                    {gpu.fallback?.reason ?? 'GPU not available'}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="h-24 flex items-center justify-center">
              <div className="text-jarvis-text-dim text-xs font-mono animate-pulse">Loading GPU data…</div>
            </div>
          )}
        </HudFrame>
      </div>

      {/* ── Metric Cards ── */}
      <m.div
        className="grid grid-cols-2 sm:grid-cols-4 gap-4"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <HudFrame className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Server size={14} className="text-jarvis-cyan" />
            <span className="metric-label text-jarvis-text-dim">Services</span>
          </div>
          <div className="flex items-baseline gap-2">
            <AnimatedCounter value={allServicesOk ? 3 : 0} suffix={`/${3}`} />
          </div>
          <p className="text-jarvis-text-dim/60 text-[10px] font-mono mt-1">{allServicesOk ? 'All online' : 'Some degraded'}</p>
        </HudFrame>

        <HudFrame className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <Cpu size={14} className={gpuStatus && gpuStatus.utilization.gpuPercent > 80 ? 'text-jarvis-red' : 'text-jarvis-cyan'} />
            <span className="metric-label text-jarvis-text-dim">GPU</span>
          </div>
          <div className="flex items-baseline gap-2">
            <AnimatedCounter value={gpuStatus ? Math.round(gpuStatus.utilization.gpuPercent) : 0} suffix="%" />
          </div>
          <p className="text-jarvis-text-dim/60 text-[10px] font-mono mt-1">{gpuStatus ? `${gpuStatus.activeDevice}` : 'N/A'}</p>
        </HudFrame>

        <HudFrame className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <HardDrive size={14} className="text-jarvis-purple" />
            <span className="metric-label text-jarvis-text-dim">VRAM</span>
          </div>
          <div className="flex items-baseline gap-2">
            <AnimatedCounter value={gpu ? +(gpu.vram.usedMb / 1024).toFixed(1) : 0} suffix={`/${gpu ? (gpu.vram.totalMb / 1024).toFixed(1) : '0'}G`} decimals={1} />
          </div>
          <p className="text-jarvis-text-dim/60 text-[10px] font-mono mt-1">{gpu ? `${(gpu.vram.usedMb / gpu.vram.totalMb * 100).toFixed(0)}% utilized` : 'N/A'}</p>
        </HudFrame>

        <HudFrame className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 size={14} className="text-jarvis-green" />
            <span className="metric-label text-jarvis-text-dim">Provider</span>
          </div>
          <div className="flex items-baseline gap-2">
            <AnimatedCounter value={activeProviderCount} suffix="" />
            <span className="text-xs font-mono text-jarvis-text-dim/60">active</span>
          </div>
          <p className="text-jarvis-text-dim/60 text-[10px] font-mono mt-1">{providers?.primary?.name ?? 'No provider'}</p>
        </HudFrame>
      </m.div>

      {/* ── Bottom: Quick Actions + Features + Tab Nav ── */}
      <div className="space-y-4">
        {/* Tab Navigation */}
        <HudFrame className="p-3">
          <div className="flex items-center gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`px-4 py-2 rounded-lg text-xs font-mono tracking-wider transition-all duration-200 cursor-pointer ${
                  activeTab === tab.key
                    ? 'text-jarvis-cyan bg-jarvis-cyan/10 border border-jarvis-cyan/30'
                    : 'text-jarvis-text-dim/60 hover:text-jarvis-text hover:bg-jarvis-bg-2/50 border border-transparent'
                }`}
              >
                {tab.label}
              </button>
            ))}
            <div className="flex-1" />
            <span className="text-[10px] font-mono text-jarvis-text-dim/30 tracking-wider">
              {activeTab.toUpperCase()} MODE
            </span>
          </div>
        </HudFrame>

        {/* Tab Content */}
        {activeTab === 'overview' && (
          <m.div
            className="space-y-4"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
          >
            {/* Quick Actions */}
            <div className="grid grid-cols-4 gap-3">
              <QuickActionButton to="/chat" icon={<MessageSquare size={16} />} label="Chat" color="var(--jarvis-cyan)" />
              <QuickActionButton to="/search" icon={<Search size={16} />} label="Search" color="var(--jarvis-blue)" />
              <QuickActionButton to="/memory" icon={<Database size={16} />} label="Memory" color="var(--jarvis-green)" />
              <QuickActionButton to="/gpu" icon={<Cpu size={16} />} label="GPU" color="var(--jarvis-purple)" />
            </div>

            {/* Features */}
            {features && (
              <HudFrame className="p-5">
                <div className="flex items-center gap-2 mb-4">
                  <Boxes size={14} className="text-jarvis-cyan" />
                  <span className="text-jarvis-cyan text-xs font-mono font-bold tracking-[0.15em] uppercase">FEATURES</span>
                  <span className="text-jarvis-text-dim text-[10px] font-mono ml-auto">{Object.values(features).filter(Boolean).length} enabled</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {(Object.entries(features) as [keyof FeatureFlags, boolean][]).map(([key, enabled]) => (
                    <FeaturePill
                      key={key}
                      name={FEATURE_LABELS[key]}
                      enabled={enabled}
                      route={FEATURE_ROUTES[key]}
                      icon={FEATURE_ICONS[key]}
                    />
                  ))}
                </div>
              </HudFrame>
            )}
          </m.div>
        )}

        {activeTab === 'diagnostics' && (
          <HudFrame className="p-6 flex items-center justify-center">
            <p className="text-jarvis-text-dim text-sm font-mono">Detailed diagnostics panel — coming soon</p>
          </HudFrame>
        )}

        {activeTab === 'network' && (
          <HudFrame className="p-6 flex items-center justify-center">
            <p className="text-jarvis-text-dim text-sm font-mono">Network monitoring — coming soon</p>
          </HudFrame>
        )}

        {activeTab === 'security' && (
          <HudFrame className="p-6 flex items-center justify-center">
            <div className="flex items-center gap-3">
              <Shield size={24} className="text-jarvis-green/50" />
              <p className="text-jarvis-text-dim text-sm font-mono">All systems secure — no threats detected</p>
            </div>
          </HudFrame>
        )}

        {activeTab === 'aicore' && (
          <HudFrame className="p-6 flex items-center justify-center">
            <p className="text-jarvis-text-dim text-sm font-mono">AI Core analytics — coming soon</p>
          </HudFrame>
        )}
      </div>

      {/* Status bar at bottom */}
      <HudFrame className="p-4">
        <div className="flex items-center justify-center gap-3">
          <m.div
            className={`w-2 h-2 rounded-full ${allServicesOk ? 'bg-jarvis-green' : 'bg-jarvis-yellow'}`}
            animate={allServicesOk ? { scale: [1, 1.2, 1], opacity: [1, 0.6, 1] } : undefined}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
          />
          <span className="text-jarvis-text-bright text-sm font-mono tracking-wider">
            {allServicesOk ? 'ALL SYSTEMS OPERATIONAL' : 'SYSTEM DEGRADED'}
          </span>
          <span className="text-jarvis-text-dim/40 text-[10px] font-mono">
            {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })}
          </span>
        </div>
      </HudFrame>
    </div>
  );
}
