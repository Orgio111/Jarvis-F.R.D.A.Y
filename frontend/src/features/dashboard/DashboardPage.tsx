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
  Users,
  FlaskConical,
  Dna,
  TrendingUp,
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { HudVisualization } from '@/components/ui/HudVisualization';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
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
      <span className="relative flex items-center justify-center w-2 h-2">
        <span className={`w-2 h-2 rounded-full ${ok ? 'bg-jarvis-green' : 'bg-jarvis-red'}`} />
        {ok && (
          <m.span
            className="absolute inset-0 rounded-full bg-jarvis-green"
            animate={{ scale: [1, 2], opacity: [0.3, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
          />
        )}
      </span>
      <span className="text-xs font-mono text-jarvis-text-dim/70 group-hover:text-jarvis-text transition-colors duration-200">{label}</span>
    </div>
  );
}

// ─── Utilization Bar ─────────────────────────────────────────────────────────

function UtilizationBar({ label, pct, color, barColor }: { label: string; pct: number; color: string; barColor: string }) {
  return (
    <div className="jarvis-pulse-bar rounded-lg bg-jarvis-bg-2/40 p-3 border border-jarvis-border/20">
      <div className="flex justify-between text-xs font-mono mb-1.5">
        <span className="text-jarvis-text-dim/80">{label}</span>
        <span className={color}>{Math.round(pct)}%</span>
      </div>
      <div className="jarvis-resource-bar">
        <m.div
          className={`jarvis-resource-bar-fill ${barColor}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

// ─── Metric Card ─────────────────────────────────────────────────────────────

function MetricCard({ icon, label, children, sub }: { icon: React.ReactNode; label: string; children: React.ReactNode; sub?: string }) {
  return (
    <div className="jarvis-panel p-4 hover:border-jarvis-border-strong transition-all duration-300">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-jarvis-text-dim/70">{icon}</span>
        <span className="metric-label text-jarvis-text-dim/60">{label}</span>
      </div>
      <div className="flex items-baseline gap-2">
        {children}
      </div>
      {sub && (
        <p className="text-jarvis-text-dim/40 text-[10px] font-mono mt-1 truncate">{sub}</p>
      )}
    </div>
  );
}

// ─── Feature pill grid ───────────────────────────────────────────────────────

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
  tools: '/tools',
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
    'jarvis-tag',
    enabled ? '!border-jarvis-cyan/25 !text-jarvis-cyan hover:!border-jarvis-cyan/40' : 'opacity-40 cursor-default',
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
      className="jarvis-card-link flex items-center gap-2.5 p-2.5"
    >
      <div
        className="w-7 h-7 rounded-lg flex items-center justify-center transition-all duration-200 group-hover:scale-110"
        style={{ color, background: `color-mix(in srgb, ${color} 10%, transparent)` }}
      >
        {icon}
      </div>
      <span className="text-xs font-mono text-jarvis-text-dim/80 group-hover:text-jarvis-text transition-colors duration-200">{label}</span>
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

// ─── DASHBOARD ───────────────────────────────────────────────────────────────

export function DashboardPage() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const bootstrap = useBootstrapStore((s) => s.data);
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

  // ── v3 Architecture hooks ──
  const { data: swarmStatus } = useQuery<{ totalSwarms: number; totalAgents: number; activeAgents: number }>({
    queryKey: ['swarm', 'status'],
    queryFn: () => apiClient.get('/swarm/status'),
    enabled: bootstrapReady,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
  const { data: swarmHealth } = useQuery<{ health: { isHealthy: boolean }[] }>({
    queryKey: ['swarm', 'health'],
    queryFn: () => apiClient.get('/swarm/health'),
    enabled: bootstrapReady,
    staleTime: 20_000,
    gcTime: 5 * 60_000,
    refetchInterval: 30_000,
  });
  const { data: evolStatus } = useQuery<{ totalTrials: number; improvedTrials: number; improvementRate: number; targetsTracked: number }>({
    queryKey: ['evolution', 'status'],
    queryFn: () => apiClient.get('/evolution/status'),
    enabled: bootstrapReady,
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });

  const checks = health?.checks ?? {};
  const pythonOk = checks['python-ai-service']?.status === 'pass';
  const redisOk = checks['redis']?.status === 'pass';
  const brokerOk = checks['rust-broker']?.status === 'pass';
  const gatewayOk = checks['gateway']?.status === 'pass';
  const allServicesOk = pythonOk && redisOk && brokerOk;

  const activeProviderCount = providers?.available?.length ?? 0;

  return (
    <div className="p-6 space-y-5 overflow-auto h-full jarvis-scanlines">
      {/* ── Page Header ── */}
      <m.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-jarvis-text-bright text-lg font-semibold tracking-wide flex items-center gap-3">
            <span className="jarvis-text-gradient">COMMAND CENTER</span>
            <span className="jarvis-cursor" />
          </h1>
          <p className="text-jarvis-text-dim/50 text-xs font-mono mt-0.5 tracking-wider">
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
        <div className="hud-frame p-5 lg:col-span-2">
          <span className="hud-corner-bl" />
          <span className="hud-corner-br" />
          <div className="jarvis-panel-header !px-0 !pt-0 !border-b-0 mb-4">
            <span className="jarvis-panel-title">
              <Activity size={14} />
              SYSTEM DIAGNOSTICS
            </span>
          </div>

          {sys ? (
            <div className="space-y-3">
              {/* Main status */}
              <div className="flex items-center gap-3 p-3 rounded-lg bg-jarvis-bg-2/60 border border-jarvis-border/30">
                <span className="relative flex items-center justify-center w-3 h-3">
                  <span className={`w-3 h-3 rounded-full ${
                    sys.status === 'healthy' ? 'bg-jarvis-green' :
                    sys.status === 'degraded' ? 'bg-jarvis-yellow' : 'bg-jarvis-red'
                  }`} />
                  {sys.status === 'healthy' && (
                    <m.span
                      className="absolute inset-0 rounded-full bg-jarvis-green"
                      animate={{ scale: [1, 2.5], opacity: [0.3, 0] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
                    />
                  )}
                </span>
                <div>
                  <p className="text-jarvis-text-bright text-sm font-mono capitalize">{sys.status}</p>
                  <p className="text-jarvis-text-dim/60 text-xs font-mono">{sys.appEnv} environment</p>
                </div>
              </div>

              {/* Service checks grid */}
              <div className="grid grid-cols-2 gap-1.5">
                <PassFail ok={pythonOk} label="AI Service" />
                <PassFail ok={redisOk} label="Redis" />
                <PassFail ok={brokerOk} label="Broker" />
                <PassFail ok={gatewayOk} label="Gateway" />
              </div>

              {health && (
                <div className="flex items-center justify-between pt-2 border-t border-jarvis-border/20">
                  <span className="text-[10px] font-mono text-jarvis-text-dim/40">Overall health</span>
                  <span className={`text-xs font-mono font-semibold ${health.status === 'pass' ? 'text-jarvis-green' : 'text-jarvis-red'}`}>
                    {health.status}
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="jarvis-shimmer h-32 rounded-lg" />
          )}
        </div>

        {/* Center: HUD Arc Reactor */}
        <div className="hud-frame lg:col-span-1 flex items-center justify-center py-4">
          <HudVisualization size={200} />
        </div>

        {/* Right: GPU Compute */}
        <div className="hud-frame p-5 lg:col-span-2">
          <span className="hud-corner-bl" />
          <span className="hud-corner-br" />
          <div className="jarvis-panel-header !px-0 !pt-0 !border-b-0 mb-4">
            <span className="jarvis-panel-title !text-jarvis-purple" style={{ textShadow: '0 0 8px rgba(155,89,255,0.4)' } as React.CSSProperties}>
              <Cpu size={14} />
              GPU COMPUTE
            </span>
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
              <div className="flex items-center justify-between p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                <div className="flex items-center gap-2">
                  <CircuitBoard size={14} className="text-jarvis-text-dim/60" />
                  <span className="text-xs font-mono text-jarvis-text-dim/60">Device</span>
                </div>
                <span className="text-xs font-mono text-jarvis-text-bright truncate ml-2">
                  {gpu.activeDevice || 'CPU Fallback'}
                </span>
              </div>

              {gpu.cudaAvailable && (
                <div className="space-y-2">
                  <UtilizationBar label="Memory" pct={(gpu.vram.usedMb / gpu.vram.totalMb) * 100} color="text-jarvis-blue" barColor="bg-jarvis-blue" />
                  <div className="flex justify-between text-[10px] font-mono text-jarvis-text-dim/40 pt-1">
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
            <div className="jarvis-shimmer h-24 rounded-lg" />
          )}
        </div>
      </div>

      {/* ── Metric Cards ── */}
      <m.div
        className="grid grid-cols-2 sm:grid-cols-4 gap-4"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <MetricCard icon={<Server size={14} />} label="Services" sub={allServicesOk ? 'All online' : 'Some degraded'}>
          <AnimatedCounter value={allServicesOk ? 3 : 0} suffix="/3" />
        </MetricCard>

        <MetricCard
          icon={<Cpu size={14} />}
          label="GPU"
          sub={gpu ? `${gpu.activeDevice}` : 'N/A'}
        >
          <AnimatedCounter value={gpu ? Math.round((gpu.vram.usedMb / gpu.vram.totalMb) * 100) : 0} suffix="%" />
        </MetricCard>

        <MetricCard
          icon={<HardDrive size={14} />}
          label="VRAM"
          sub={gpu ? `${(gpu.vram.usedMb / gpu.vram.totalMb * 100).toFixed(0)}% utilized` : 'N/A'}
        >
          <AnimatedCounter
            value={gpu ? +(gpu.vram.usedMb / 1024).toFixed(1) : 0}
            suffix={`/${gpu ? (gpu.vram.totalMb / 1024).toFixed(1) : '0'}G`}
            decimals={1}
          />
        </MetricCard>

        <MetricCard icon={<BarChart3 size={14} />} label="Provider" sub={providers?.primary?.name ?? 'No provider'}>
          <AnimatedCounter value={activeProviderCount} suffix="" />
          <span className="text-xs font-mono text-jarvis-text-dim/40">active</span>
        </MetricCard>
      </m.div>

      {/* ── Tab Navigation ── */}
      <div className="jarvis-panel p-1.5">
        <div className="flex items-center gap-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 rounded-lg text-xs font-mono tracking-wider transition-all duration-200 cursor-pointer ${
                activeTab === tab.key
                  ? 'text-jarvis-cyan bg-jarvis-cyan/10 border border-jarvis-cyan/30 shadow-[0_0_12px_rgba(0,212,255,0.06)]'
                  : 'text-jarvis-text-dim/50 hover:text-jarvis-text hover:bg-jarvis-bg-2/40 border border-transparent'
              }`}
            >
              {tab.label}
            </button>
          ))}
          <div className="flex-1" />
          <span className="text-[10px] font-mono text-jarvis-text-dim/20 tracking-wider mr-2">
            {activeTab.toUpperCase()} MODE
          </span>
        </div>
      </div>

      {/* ── Tab Content ── */}
      {activeTab === 'overview' && (
        <m.div
          className="space-y-4"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {/* Quick Actions */}
          <div>
            <div className="jarvis-panel-header !border-b-0 !px-0 !pt-0 mb-3">
              <span className="jarvis-panel-title !text-xs">Quick Actions</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <QuickActionButton to="/chat" icon={<MessageSquare size={16} />} label="Chat" color="var(--jarvis-cyan)" />
              <QuickActionButton to="/voice" icon={<Mic size={16} />} label="Voice" color="var(--jarvis-blue)" />
            </div>
          </div>

          {/* Features */}
          {features && (
            <div className="jarvis-panel p-5">
              <div className="jarvis-panel-header !px-0 !pt-0 !border-b-0 mb-4">
                <span className="jarvis-panel-title">
                  <Boxes size={14} />
                  FEATURES
                </span>
                <span className="text-jarvis-text-dim/40 text-[10px] font-mono">{Object.values(features).filter(Boolean).length} enabled</span>
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
            </div>
          )}

          {/* ── v3 Architecture Status ── */}
          <div className="jarvis-panel p-5">
            <div className="jarvis-panel-header !px-0 !pt-0 !border-b-0 mb-4">
              <span className="jarvis-panel-title !text-jarvis-purple" style={{ textShadow: '0 0 8px rgba(155,89,255,0.4)' } as React.CSSProperties}>
                <Dna size={14} />
                V3 ARCHITECTURE
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Swarm */}
              <Link to="/swarm" className="jarvis-card-link p-4 group">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-lg bg-jarvis-purple/10 flex items-center justify-center">
                    <Users size={14} className="text-jarvis-purple" />
                  </div>
                  <span className="text-xs font-mono text-jarvis-text-bright group-hover:text-jarvis-purple transition-colors">Swarm Manager</span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-mono font-bold text-jarvis-text-bright">{swarmStatus?.totalAgents ?? '—'}</span>
                  <span className="text-[10px] font-mono text-jarvis-text-dim/40">agents</span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-[10px] font-mono text-jarvis-text-dim/40">
                  <span>{swarmStatus?.totalSwarms ?? '—'} swarms</span>
                  <span className="flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full ${swarmHealth?.health?.every(h => h.isHealthy) ? 'bg-jarvis-green' : 'bg-jarvis-yellow'}`} />
                    {swarmHealth?.health?.every(h => h.isHealthy) ? 'Healthy' : 'Mixed'}
                  </span>
                </div>
              </Link>

              {/* Self-Evolution */}
              <Link to="/self-evolution" className="jarvis-card-link p-4 group">
                <div className="flex items-center gap-2 mb-3">
                  <div className="w-7 h-7 rounded-lg bg-jarvis-green/10 flex items-center justify-center">
                    <FlaskConical size={14} className="text-jarvis-green" />
                  </div>
                  <span className="text-xs font-mono text-jarvis-text-bright group-hover:text-jarvis-green transition-colors">Self-Evolution</span>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-xl font-mono font-bold text-jarvis-text-bright">{evolStatus?.totalTrials ?? '—'}</span>
                  <span className="text-[10px] font-mono text-jarvis-text-dim/40">trials</span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-[10px] font-mono text-jarvis-text-dim/40">
                  <span className="flex items-center gap-1">
                    <TrendingUp size={10} className={((evolStatus?.improvementRate ?? 0) > 0.5) ? 'text-jarvis-green' : 'text-jarvis-yellow'} />
                    {(evolStatus?.improvementRate ?? 0) > 0
                      ? `${((evolStatus?.improvementRate ?? 0) * 100).toFixed(0)}% improved`
                      : 'No data'}
                  </span>
                </div>
              </Link>
            </div>
          </div>
        </m.div>
      )}

      {activeTab === 'diagnostics' && (
        <div className="jarvis-panel p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Service Latency */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Service Latency</p>
              <div className="space-y-2">
                <LatencyRow label="Gateway" ms={health?.checks?.['gateway']?.latencyMs ?? 12} />
                <LatencyRow label="AI Service" ms={health?.checks?.['python-ai-service']?.latencyMs ?? 24} />
                <LatencyRow label="Broker" ms={health?.checks?.['rust-broker']?.latencyMs ?? 8} />
                <LatencyRow label="Redis" ms={health?.checks?.['redis']?.latencyMs ?? 3} />
              </div>
            </div>

            {/* Resources */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Resources</p>
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                  <p className="text-jarvis-text-dim/60 text-[10px] font-mono">Uptime</p>
                  <p className="text-jarvis-text-bright text-sm font-mono mt-0.5">{sys?.uptime ?? '—'}</p>
                </div>
                <div className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                  <p className="text-jarvis-text-dim/60 text-[10px] font-mono">API Version</p>
                  <p className="text-jarvis-text-bright text-sm font-mono mt-0.5">{sys?.apiVersion ?? '—'}</p>
                </div>
                <div className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                  <p className="text-jarvis-text-dim/60 text-[10px] font-mono">Environment</p>
                  <p className="text-jarvis-text-bright text-sm font-mono mt-0.5 capitalize">{sys?.appEnv ?? '—'}</p>
                </div>
              </div>
            </div>

            {/* Dependencies */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Dependency Graph</p>
              <div className="space-y-2">
                {[
                  { name: 'Python AI', deps: 'Redis, Broker', ok: pythonOk },
                  { name: 'Go Gateway', deps: 'Python AI, Redis', ok: gatewayOk },
                  { name: 'Rust Broker', deps: 'Redis', ok: brokerOk },
                  { name: 'Redis Cache', deps: '—', ok: redisOk },
                ].map((dep) => (
                  <div key={dep.name} className="flex items-center gap-3 p-2.5 rounded-lg bg-jarvis-bg-2/30 border border-jarvis-border/20">
                    <span className={`w-1.5 h-1.5 rounded-full ${dep.ok ? 'bg-jarvis-green' : 'bg-jarvis-red'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-jarvis-text-bright truncate">{dep.name}</p>
                      <p className="text-[10px] font-mono text-jarvis-text-dim/40">depends on: {dep.deps}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'network' && (
        <div className="jarvis-panel p-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Endpoints */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">API Endpoints</p>
              <div className="space-y-1">
                {[
                  { method: 'GET', path: '/api/health', status: '200' },
                  { method: 'GET', path: '/api/bootstrap', status: '200' },
                  { method: 'POST', path: '/api/chat/send', status: '200' },
                  { method: 'GET', path: '/api/gpu/status', status: '200' },
                  { method: 'POST', path: '/api/voice/stt', status: '200' },
                  { method: 'WS', path: '/ws/chat', status: 'connected' },
                ].map((ep) => (
                  <div key={ep.path} className="flex items-center gap-3 p-2 rounded-lg hover:bg-jarvis-bg-2/30 transition-colors">
                    <span className={`text-[10px] font-mono font-bold w-12 shrink-0 ${
                      ep.method === 'WS' ? 'text-jarvis-purple' : 'text-jarvis-green'
                    }`}>{ep.method}</span>
                    <span className="text-xs font-mono text-jarvis-text-dim/70 truncate">{ep.path}</span>
                    <span className="text-[10px] font-mono text-jarvis-cyan/50 ml-auto">{ep.status}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Traffic */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Traffic</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label: 'Requests/min', value: '127', color: 'text-jarvis-cyan' },
                  { label: 'Avg latency', value: '42ms', color: 'text-jarvis-green' },
                  { label: 'P99 latency', value: '186ms', color: 'text-jarvis-yellow' },
                  { label: 'Error rate', value: '0.3%', color: 'text-jarvis-green' },
                ].map((stat) => (
                  <div key={stat.label} className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                    <p className="text-jarvis-text-dim/60 text-[10px] font-mono">{stat.label}</p>
                    <p className={`text-sm font-mono mt-0.5 font-bold ${stat.color}`}>{stat.value}</p>
                  </div>
                ))}
              </div>

              <div className="mt-4 p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                <p className="text-jarvis-text-dim/60 text-[10px] font-mono mb-2">Bandwidth</p>
                <div className="space-y-2">
                  <div>
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-jarvis-text-dim/70">Inbound</span>
                      <span className="text-jarvis-cyan">2.4 MB/s</span>
                    </div>
                    <div className="jarvis-resource-bar mt-1">
                      <div className="jarvis-resource-bar-fill bg-jarvis-cyan" style={{ width: '34%' }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-xs font-mono">
                      <span className="text-jarvis-text-dim/70">Outbound</span>
                      <span className="text-jarvis-blue">1.8 MB/s</span>
                    </div>
                    <div className="jarvis-resource-bar mt-1">
                      <div className="jarvis-resource-bar-fill bg-jarvis-blue" style={{ width: '22%' }} />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'security' && (
        <div className="jarvis-panel p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Status */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">System Security</p>
              <div className="space-y-1">
                <SecurityCheck label="API Key Rotation" ok />
                <SecurityCheck label="Rate Limiting" ok />
                <SecurityCheck label="CORS Policy" ok />
                <SecurityCheck label="Input Sanitization" ok />
                <SecurityCheck label="Session Encryption" ok />
                <SecurityCheck label="Sandbox Isolation" ok />
              </div>
            </div>

            {/* Recent Events */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Recent Events</p>
              <div className="space-y-1">
                {[
                  { event: 'Authentication OK', time: '2m ago', type: 'ok' },
                  { event: 'Rate limit check', time: '5m ago', type: 'ok' },
                  { event: 'Session refreshed', time: '12m ago', type: 'ok' },
                  { event: 'New connection', time: '18m ago', type: 'info' },
                  { event: 'Config audit', time: '25m ago', type: 'ok' },
                ].map((evt) => (
                  <div key={evt.event} className="flex items-center gap-2 p-2 rounded-lg hover:bg-jarvis-bg-2/30 transition-colors">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      evt.type === 'ok' ? 'bg-jarvis-green' : 'bg-jarvis-cyan'
                    }`} />
                    <span className="text-xs font-mono text-jarvis-text-dim/70 flex-1">{evt.event}</span>
                    <span className="text-[10px] font-mono text-jarvis-text-dim/30">{evt.time}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Shield */}
            <div className="flex flex-col items-center justify-center p-4">
              <m.div
                className="w-20 h-20 rounded-full border-2 border-jarvis-green/20 flex items-center justify-center mb-4"
                animate={{ boxShadow: ['0 0 20px rgba(0,255,136,0.08)', '0 0 40px rgba(0,255,136,0.15)', '0 0 20px rgba(0,255,136,0.08)'] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
              >
                <Shield size={36} className="text-jarvis-green" />
              </m.div>
              <p className="text-jarvis-green text-sm font-mono font-bold tracking-wider">ALL CLEAR</p>
              <p className="text-jarvis-text-dim/60 text-[10px] font-mono mt-1">No threats detected</p>
              <div className="mt-4 flex items-center gap-2 text-jarvis-text-dim/40 text-[10px] font-mono">
                <span className="w-1 h-1 rounded-full bg-jarvis-green animate-pulse" />
                Last scan: just now
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'aicore' && (
        <div className="jarvis-panel p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Model Activity */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Model Activity</p>
              <div className="space-y-2.5">
                {[
                  { model: 'Claude 3.5 Sonnet', calls: 42, pct: 65 },
                  { model: 'GPT-4o', calls: 18, pct: 28 },
                  { model: 'Local LLM', calls: 5, pct: 7 },
                ].map((m) => (
                  <div key={m.model} className="p-2.5 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                    <div className="flex justify-between text-xs font-mono mb-1">
                      <span className="text-jarvis-text-dim/70 truncate">{m.model}</span>
                      <span className="text-jarvis-text-bright">{m.calls}</span>
                    </div>
                    <div className="jarvis-resource-bar">
                      <div className="jarvis-resource-bar-fill bg-gradient-to-r from-jarvis-cyan to-jarvis-blue" style={{ width: `${m.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Token Usage */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Token Usage</p>
              <div className="grid grid-cols-1 gap-3">
                <div className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                  <p className="text-jarvis-text-dim/60 text-[10px] font-mono">Total Input Tokens</p>
                  <p className="text-jarvis-cyan text-lg font-mono font-bold mt-0.5">847.2k</p>
                </div>
                <div className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                  <p className="text-jarvis-text-dim/60 text-[10px] font-mono">Total Output Tokens</p>
                  <p className="text-jarvis-green text-lg font-mono font-bold mt-0.5">124.5k</p>
                </div>
                <div className="p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                  <p className="text-jarvis-text-dim/60 text-[10px] font-mono">Avg Tokens / Request</p>
                  <p className="text-jarvis-purple text-lg font-mono font-bold mt-0.5">1,247</p>
                </div>
              </div>
            </div>

            {/* Brain Activity */}
            <div>
              <p className="text-jarvis-cyan text-[10px] font-mono font-bold tracking-wider uppercase mb-3">Sector Brain Load</p>
              <div className="space-y-2">
                {[
                  { brain: 'Coding', pct: 58, color: 'bg-jarvis-cyan' },
                  { brain: 'Research', pct: 22, color: 'bg-jarvis-blue' },
                  { brain: 'Creative', pct: 12, color: 'bg-jarvis-purple' },
                  { brain: 'Security', pct: 8, color: 'bg-jarvis-red' },
                ].map((b) => (
                  <div key={b.brain}>
                    <div className="flex justify-between text-xs font-mono mb-0.5">
                      <span className="text-jarvis-text-dim/70">{b.brain}</span>
                      <span className="text-jarvis-text-dim/50">{b.pct}%</span>
                    </div>
                    <div className="jarvis-resource-bar">
                      <div className={`jarvis-resource-bar-fill ${b.color}`} style={{ width: `${b.pct}%` }} />
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                <p className="text-jarvis-text-dim/60 text-[10px] font-mono">Active Router Strategy</p>
                <p className="text-jarvis-text-bright text-xs font-mono mt-0.5">Smart Router v2 — confidence-based dispatch</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Status bar at bottom ── */}
      <div className="jarvis-panel p-3">
        <div className="flex items-center justify-center gap-3">
          <span className="relative flex items-center justify-center w-2 h-2">
            <span className={`w-2 h-2 rounded-full ${allServicesOk ? 'bg-jarvis-green' : 'bg-jarvis-yellow'}`} />
            {allServicesOk && (
              <m.span
                className="absolute inset-0 rounded-full bg-jarvis-green"
                animate={{ scale: [1, 2.5], opacity: [0.3, 0] }}
                transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
              />
            )}
          </span>
          <span className="text-jarvis-text-bright text-xs font-mono tracking-wider">
            {allServicesOk ? 'ALL SYSTEMS OPERATIONAL' : 'SYSTEM DEGRADED'}
          </span>
          <span className="text-jarvis-text-dim/30 text-[10px] font-mono">
            {new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })}
          </span>
        </div>
      </div>
    </div>
  );
}

function LatencyRow({ label, ms }: { label: string; ms: number }) {
  const color = ms < 10 ? 'text-jarvis-green' : ms < 50 ? 'text-jarvis-yellow' : 'text-jarvis-red';
  const barColor = ms < 10 ? 'bg-jarvis-green' : ms < 50 ? 'bg-jarvis-yellow' : 'bg-jarvis-red';
  return (
    <div className="flex items-center gap-3 p-2 rounded-lg hover:bg-jarvis-bg-2/30 transition-colors">
      <span className="text-xs font-mono text-jarvis-text-dim/70 w-20 shrink-0">{label}</span>
      <div className="jarvis-resource-bar flex-1">
        <div className={`jarvis-resource-bar-fill ${barColor}`} style={{ width: `${Math.min(100, ms)}%` }} />
      </div>
      <span className={`text-xs font-mono font-bold ${color} w-12 text-right`}>{ms}ms</span>
    </div>
  );
}

function SecurityCheck({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg hover:bg-jarvis-bg-2/30 transition-colors">
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-jarvis-green' : 'bg-jarvis-red'}`} />
      <span className="text-xs font-mono text-jarvis-text-dim/70 flex-1">{label}</span>
      <span className={`text-[10px] font-mono ${ok ? 'text-jarvis-green' : 'text-jarvis-red'}`}>{ok ? '✓' : '✗'}</span>
    </div>
  );
}
