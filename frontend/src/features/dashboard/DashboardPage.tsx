import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import type { HealthResponse, FeatureFlags } from '@/lib/api/types';

// ─── Status badge ─────────────────────────────────────────────────────────────

function PassFail({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-xs font-mono ${ok ? 'text-green-400' : 'text-jarvis-red'}`}>
        {ok ? '✓' : '✗'}
      </span>
      <span className="text-jarvis-text-dim text-xs font-mono">{label}</span>
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

function FeaturePill({ name, enabled, route }: { name: string; enabled: boolean; route?: string }) {
  const cls = [
    'px-2.5 py-1 rounded text-xs font-mono border transition-colors',
    enabled
      ? 'border-jarvis-cyan/30 text-jarvis-cyan bg-jarvis-cyan/5 hover:bg-jarvis-cyan/10'
      : 'border-jarvis-border text-jarvis-text-dim opacity-40',
  ].join(' ');

  if (enabled && route) {
    return <Link to={route} className={cls}>{name}</Link>;
  }
  return <span className={cls}>{name}</span>;
}

// ─── Quick-action card ────────────────────────────────────────────────────────

function QuickCard({ to, icon, label, sub }: { to: string; icon: string; label: string; sub: string }) {
  return (
    <Link
      to={to}
      className="jarvis-panel p-4 rounded flex flex-col gap-1 hover:border-jarvis-cyan/40 hover:bg-jarvis-cyan/5 transition-colors group"
    >
      <span className="text-2xl leading-none group-hover:scale-110 transition-transform">{icon}</span>
      <p className="text-jarvis-text-bright text-xs font-mono font-semibold mt-1">{label}</p>
      <p className="text-jarvis-text-dim text-xs font-mono">{sub}</p>
    </Link>
  );
}

// ─── Dashboard ────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const bootstrap = useBootstrapStore((s) => s.data);

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

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader
        title="JARVIS F.R.D.A.Y"
        subtitle={sys ? `v${sys.version} · ${sys.appEnv}` : 'AI Operating System'}
      />

      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* ── System health ── */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">System Health</p>
          {sys ? (
            <div className="space-y-2">
              <StatusDot
                status={sys.status === 'healthy' ? 'online' : sys.status === 'degraded' ? 'degraded' : 'loading'}
                label={sys.status}
              />
              <div className="mt-2 space-y-1">
                <PassFail ok={pythonOk} label="AI service" />
                <PassFail ok={redisOk} label="Redis" />
              </div>
              {health && (
                <p className="text-jarvis-text-dim text-xs font-mono mt-2 opacity-60">
                  overall: {health.status}
                </p>
              )}
            </div>
          ) : (
            <p className="text-jarvis-text-dim text-xs font-mono">Loading…</p>
          )}
        </GlassPanel>

        {/* ── Active provider ── */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">AI Provider</p>
          {providers ? (
            <div className="space-y-2">
              <StatusDot
                status={providers.primary?.status === 'available' ? 'online' : 'offline'}
                label={providers.primary?.name ?? 'none'}
              />
              <p className="text-jarvis-text-dim text-xs font-mono">
                {providers.available?.length ?? 0} provider{providers.available?.length !== 1 ? 's' : ''} available
              </p>
              {bootstrap?.models && (
                <p className="text-jarvis-cyan text-xs font-mono truncate">
                  default: {bootstrap.models.defaultChatModel || '—'}
                </p>
              )}
            </div>
          ) : (
            <p className="text-jarvis-text-dim text-xs font-mono">Loading…</p>
          )}
        </GlassPanel>

        {/* ── GPU ── */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">GPU</p>
          {gpu ? (
            <div className="space-y-2">
              <StatusDot
                status={gpu.cudaAvailable ? 'online' : 'offline'}
                label={gpu.cudaAvailable ? gpu.activeDevice : 'CPU Fallback'}
              />
              {gpu.cudaAvailable && (
                <>
                  <p className="text-jarvis-text-dim text-xs font-mono">
                    VRAM {(gpu.vram.usedMb / 1024).toFixed(1)} / {(gpu.vram.totalMb / 1024).toFixed(1)} GB
                  </p>
                  <div className="h-1 bg-jarvis-bg rounded-full overflow-hidden">
                    <div
                      className="h-full bg-jarvis-cyan rounded-full"
                      style={{ width: `${(gpu.vram.usedMb / gpu.vram.totalMb) * 100}%` }}
                    />
                  </div>
                </>
              )}
              {!gpu.cudaAvailable && (
                <p className="text-jarvis-text-dim text-xs font-mono opacity-70">
                  {gpu.fallback?.reason ?? 'No CUDA device'}
                </p>
              )}
            </div>
          ) : (
            <p className="text-jarvis-text-dim text-xs font-mono">Loading…</p>
          )}
        </GlassPanel>
      </div>

      {/* ── Features grid ── */}
      {features && (
        <GlassPanel className="p-5 mt-4">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Features</p>
          <div className="flex flex-wrap gap-2">
            {(Object.entries(features) as [keyof FeatureFlags, boolean][]).map(([key, enabled]) => (
              <FeaturePill
                key={key}
                name={FEATURE_LABELS[key]}
                enabled={enabled}
                route={FEATURE_ROUTES[key]}
              />
            ))}
          </div>
        </GlassPanel>
      )}

      {/* ── Quick actions ── */}
      <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
        <QuickCard to="/chat"            icon="◈" label="Chat"         sub="Talk to JARVIS" />
        <QuickCard to="/search"          icon="◌" label="Search"       sub="Web search" />
        <QuickCard to="/memory"          icon="◫" label="Memory"       sub="Vector store" />
        <QuickCard to="/monitoring"      icon="◎" label="Monitor"      sub="System metrics" />
        <QuickCard to="/local-actions"   icon="◧" label="Actions"      sub="Run commands" />
      </div>
    </div>
  );
}
