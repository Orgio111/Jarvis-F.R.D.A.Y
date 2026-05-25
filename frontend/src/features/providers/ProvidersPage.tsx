import { useState } from 'react';
import { RefreshCw, Radio, Satellite, ChevronDown, ChevronUp, Globe, Zap, Gift, List, Cpu } from 'lucide-react';

import { useProviders, useDiscoveredProviders } from './useProviders';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import type { ProviderStatus } from '@/lib/api/types';
import { cn } from '@/lib/utils';

import { m, AnimatePresence } from 'framer-motion';

export function ProvidersPage() {
  const { data: allProviders = [], isLoading } = useProviders();
  const {
    discovered,
    isLoading: discoLoading,
    isError: discoError,
    isSyncing,
    sync,
  } = useDiscoveredProviders();

  // Static providers = all providers minus discovered
  const staticProviders = allProviders.filter((p) => !p.isDiscovered);

  // Track which discovered provider card is expanded
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="p-6 overflow-auto h-full space-y-8">
      {/* ── Configured (Static) Providers ── */}
      <section>
        <SectionHeader
          title="AI Providers"
          subtitle="Configured provider status and routing"
        />

        {isLoading ? (
          <div className="text-jarvis-text-dim text-xs font-mono mt-6">Loading providers…</div>
        ) : staticProviders.length === 0 && discovered.length === 0 ? (
          <NoProviders />
        ) : staticProviders.length === 0 ? (
          <div className="text-jarvis-text-dim text-xs font-mono mt-4">
            No configured providers. Enable one via <code className="text-jarvis-cyan">.env</code>.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            {staticProviders.map((p) => (
              <ProviderCard key={p.id} provider={p} />
            ))}
          </div>
        )}
      </section>

      {/* ── Discovered Providers ── */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <SectionHeader
              title={
                <span className="inline-flex items-center gap-2">
                  <Satellite size={14} className="text-jarvis-purple" />
                  Discovered Providers
                </span>
              }
              subtitle="Dynamically detected AI endpoints"
            />
            <NeonBadge label="Beta" color="purple" size="sm" pulse />
          </div>
          <CockpitButton
            variant="glow"
            size="sm"
            icon={<RefreshCw size={13} />}
            loading={isSyncing}
            onClick={() => sync()}
          >
            Re-discover
          </CockpitButton>
        </div>

        {discoLoading ? (
          <div className="text-jarvis-text-dim text-xs font-mono mt-2">Scanning providers…</div>
        ) : discoError ? (
          <GlassPanel className="p-5">
            <p className="text-jarvis-red text-xs font-mono">Failed to load discovered providers.</p>
          </GlassPanel>
        ) : discovered.length === 0 ? (
          <GlassPanel className="p-5">
            <div className="flex items-center gap-3">
              <Radio size={16} className="text-jarvis-text-dim" />
              <p className="text-jarvis-text-dim text-xs font-mono">
                No providers discovered yet. Click <span className="text-jarvis-cyan">Re-discover</span> to scan for available endpoints.
              </p>
            </div>
          </GlassPanel>
        ) : (
          <AnimatePresence mode="popLayout">
            <m.div
              className="grid grid-cols-1 md:grid-cols-2 gap-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.3, ease: 'easeOut', staggerChildren: 0.05 }}
            >
              {discovered.map((p, i) => {
                const isExpanded = expandedId === p.id;
                return (
                  <m.div
                    key={p.id}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25, delay: i * 0.04, ease: 'easeOut' }}
                  >
                    <ProviderCard
                      provider={p}
                      expanded={isExpanded}
                      onToggle={() => setExpandedId(isExpanded ? null : p.id)}
                    />
                  </m.div>
                );
              })}
            </m.div>
          </AnimatePresence>
        )}
      </section>
    </div>
  );
}

function ProviderCard({ provider, expanded, onToggle }: { provider: ProviderStatus; expanded?: boolean; onToggle?: () => void }) {
  const isAvailable = provider.status === 'available';
  const isUnavailable = provider.status === 'provider_unavailable';
  const isDiscovered = provider.isDiscovered;

  return (
    <GlassPanel className={cn('p-5', onToggle && 'cursor-pointer')} hover={!!onToggle} onClick={onToggle}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold truncate">
              {provider.name}
            </p>
            {isDiscovered && (
              <NeonBadge label="Discovered" color="purple" size="sm" />
            )}
            {isDiscovered && provider.isFree && (
              <NeonBadge label="Free" color="green" size="sm" />
            )}
            {onToggle && (
              <span className="ml-auto text-jarvis-text-dim/50">
                {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </span>
            )}
          </div>
          <p className="text-jarvis-text-dim text-xs font-mono mt-0.5 truncate">{provider.id}</p>
          {isDiscovered && provider.latencyMs != null && (
            <p className="text-jarvis-text-dim text-xs font-mono mt-0.5">
              <span className="text-jarvis-green">{provider.latencyMs.toFixed(0)}ms</span> latency
            </p>
          )}
        </div>
        <StatusDot
          status={isAvailable ? 'online' : isUnavailable ? 'offline' : 'warning'}
          label={provider.status}
        />
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
        <div>
          <p className="text-jarvis-text-dim">Device</p>
          <p className="text-jarvis-text-bright capitalize">{provider.deviceMode}</p>
        </div>
        <div>
          <p className="text-jarvis-text-dim">Models</p>
          <p className="text-jarvis-text-bright">{provider.modelCount ?? '—'}</p>
        </div>
        {provider.isDefault && (
          <div className="col-span-2">
            <span className="text-jarvis-cyan text-xs">★ Primary</span>
          </div>
        )}
        {provider.isFallback && (
          <div className="col-span-2">
            <span className="text-jarvis-blue text-xs">↩ Fallback</span>
          </div>
        )}
      </div>

      {provider.reason && (
        <p className="mt-3 text-jarvis-text-dim text-xs font-mono border-t border-jarvis-border pt-2 break-all">
          {provider.reason}
        </p>
      )}

      {/* ── Expanded detail panel (discovered providers only) ── */}
      {expanded && isDiscovered && (
        <DiscoveredProviderDetail provider={provider} />
      )}
    </GlassPanel>
  );
}

function NoProviders() {
  return (
    <GlassPanel className="p-8 text-center mt-6 max-w-md">
      <p className="text-jarvis-text-dim text-sm font-mono">
        No providers configured.
      </p>
      <div className="text-jarvis-text-dim text-xs font-mono mt-3 space-y-1.5">
        <p>
          Add <code className="text-jarvis-cyan">NVIDIA_NIM_API_KEY</code> or{' '}
          <code className="text-jarvis-cyan">OPENROUTER_API_KEY</code> to your{' '}
          <code className="text-jarvis-cyan">.env</code> file.
        </p>
        <p className="flex items-center gap-1.5">
          <Radio size={12} />
          Or try the <span className="text-jarvis-purple">Re-discover</span> button below to scan for free endpoints.
        </p>
      </div>
    </GlassPanel>
  );
}

/** Detail panel shown when a discovered provider card is expanded. */
function DiscoveredProviderDetail({ provider }: { provider: ProviderStatus }) {
  const caps = provider.capabilities ?? [];
  const models = provider.models ?? [];
  const score = provider.score ?? 0;
  const scoreBarWidth = Math.min(score, 100);
  const isFree = provider.isFree ?? false;
  const baseUrl = provider.baseUrl ?? '';

  const scoreColor =
    score >= 70 ? 'text-jarvis-green' :
    score >= 40 ? 'text-jarvis-yellow' :
    'text-jarvis-red';

  const scoreBarColor =
    score >= 70 ? 'bg-jarvis-green' :
    score >= 40 ? 'bg-jarvis-yellow' :
    'bg-jarvis-red';

  return (
    <m.div
      className="mt-4 pt-4 border-t border-jarvis-border/50 space-y-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {/* Score gauge */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-jarvis-text-dim text-[10px] font-mono uppercase tracking-wider">
            <Zap size={11} className="inline mr-1" />
            Score
          </span>
          <span className={cn('text-xs font-mono font-semibold', scoreColor)}>
            {score.toFixed(1)}
          </span>
        </div>
        <div className="h-1.5 bg-jarvis-bg-3/60 rounded-full overflow-hidden">
          <m.div
            className={`h-full rounded-full ${scoreBarColor}`}
            initial={{ width: 0 }}
            animate={{ width: `${scoreBarWidth}%` }}
            transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
          />
        </div>
      </div>

      {/* Capabilities */}
      {caps.length > 0 && (
        <div>
          <p className="text-jarvis-text-dim text-[10px] font-mono uppercase tracking-wider mb-2">
            <Cpu size={11} className="inline mr-1" />
            Capabilities
          </p>
          <div className="flex flex-wrap gap-1.5">
            {caps.map((cap) => (
              <span
                key={cap}
                className="text-xs font-mono px-2 py-0.5 rounded-md border border-jarvis-cyan/20 text-jarvis-cyan bg-jarvis-cyan/5"
              >
                {cap}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Free badge + Base URL */}
      <div className="grid grid-cols-2 gap-3 text-xs font-mono">
        <div className="p-2.5 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
          <p className="text-jarvis-text-dim text-[10px] mb-0.5">
            <Gift size={11} className="inline mr-1" />
            Tier
          </p>
          <p className={isFree ? 'text-jarvis-green' : 'text-jarvis-text-dim'}>
            {isFree ? 'Free' : 'Paid'}
          </p>
        </div>
        <div className="p-2.5 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
          <p className="text-jarvis-text-dim text-[10px] mb-0.5">
            <Globe size={11} className="inline mr-1" />
            Endpoint
          </p>
          <p className="text-jarvis-text-bright truncate" title={baseUrl}>
            {baseUrl || '—'}
          </p>
        </div>
      </div>

      {/* Models */}
      {models.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-jarvis-text-dim text-[10px] font-mono uppercase tracking-wider">
              <List size={11} className="inline mr-1" />
              Models ({models.length})
            </p>
          </div>
          <div className="max-h-36 overflow-y-auto space-y-0.5 pr-1" style={{ scrollbarWidth: 'thin' }}>
            {models.map((m) => (
              <div
                key={m}
                className="text-xs font-mono text-jarvis-text-dim/80 px-2 py-1 rounded bg-jarvis-bg-3/30 hover:bg-jarvis-bg-3/60 hover:text-jarvis-text transition-colors"
              >
                {m}
              </div>
            ))}
          </div>
        </div>
      )}

      {models.length === 0 && (
        <p className="text-jarvis-text-dim/50 text-[10px] font-mono italic">
          No models reported.
        </p>
      )}
    </m.div>
  );
}
