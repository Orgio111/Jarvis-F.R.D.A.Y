import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Globe,
  Zap,
  Activity,
  RefreshCw,
  Play,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Shield,
  Clock,
} from 'lucide-react';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';

import { CockpitButton } from '@/components/ui/CockpitButton';
import { cn } from '@/lib/utils';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface ExternalApiProvider {
  name: string;
  description: string;
  status: 'unknown' | 'online' | 'degraded' | 'offline';
  endpointCount: number;
  tags: string[];
  score: number;
}

interface ApiCallResponse {
  success: boolean;
  data?: unknown;
  error?: string;
  provider?: string;
  latencyMs?: number;
  endpoint?: string;
}

export function ApiRegistryPanel() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const queryClient = useQueryClient();
  const [expandedProvider, setExpandedProvider] = useState<string | null>(null);

  const { data: providers = [], isLoading } = useQuery<ExternalApiProvider[]>({
    queryKey: ['external-apis', 'providers'],
    queryFn: () => apiClient.get<ExternalApiProvider[]>('/external-apis/providers'),
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });

  const { data: healthData, refetch: refetchHealth, isFetching: healthLoading } = useQuery<Record<string, string>>({
    queryKey: ['external-apis', 'health'],
    queryFn: () => apiClient.get<Record<string, string>>('/external-apis/health'),
    enabled: bootstrapReady,
    ...freshness.resourceState,
  });

  const statusColor = (status: string) => {
    switch (status) {
      case 'online': return 'bg-jarvis-green';
      case 'degraded': return 'bg-jarvis-yellow';
      case 'offline': return 'bg-jarvis-red';
      default: return 'bg-jarvis-text-dim/30';
    }
  };

  return (
    <div className="p-6 overflow-auto h-full space-y-6">
      <div className="flex items-center justify-between">
        <SectionHeader
          title={
            <span className="inline-flex items-center gap-2">
              <Globe size={16} className="text-jarvis-cyan" />
              External API Registry
            </span>
          }
          subtitle="Dynamically call free public APIs with fallback and normalization"
        />
        <div className="flex items-center gap-2">
          <CockpitButton
            variant="ghost"
            size="sm"
            icon={<Activity size={13} />}
            loading={healthLoading}
            onClick={() => refetchHealth()}
          >
            Health Check
          </CockpitButton>
          <CockpitButton
            variant="glow"
            size="sm"
            icon={<RefreshCw size={13} />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['external-apis'] })}
          >
            Refresh
          </CockpitButton>
        </div>
      </div>

      {isLoading ? (
        <div className="text-jarvis-text-dim text-xs font-mono">Loading API registry…</div>
      ) : providers.length === 0 ? (
        <GlassPanel className="p-8 text-center">
          <Globe size={40} className="mx-auto text-jarvis-text-dim/20 mb-3" />
          <p className="text-jarvis-text-dim text-sm font-mono">No external APIs registered.</p>
          <p className="text-jarvis-text-dim/50 text-xs font-mono mt-2">Register providers to enable external API calls.</p>
        </GlassPanel>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          <AnimatePresence mode="popLayout">
            {providers.map((provider, i) => {
              const isExpanded = expandedProvider === provider.name;
              const healthStatus = healthData?.[provider.name] ?? provider.status;

              return (
                <m.div
                  key={provider.name}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.25, delay: i * 0.04, ease: 'easeOut' }}
                >
                  <GlassPanel
                    className="p-5 cursor-pointer"
                    hover
                    onClick={() => setExpandedProvider(isExpanded ? null : provider.name)}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="text-jarvis-text-bright text-sm font-mono font-semibold truncate">
                            {provider.name}
                          </p>
                          <NeonBadge label={provider.endpointCount.toString()} color="cyan" size="sm" />
                          {provider.tags.map((tag) => (
                            <span
                              key={tag}
                              className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-jarvis-border/30 text-jarvis-text-dim/60"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                        <p className="text-jarvis-text-dim text-xs font-mono mt-0.5">{provider.description}</p>
                        <div className="flex items-center gap-3 mt-1 text-xs font-mono text-jarvis-text-dim/50">
                          <span className="flex items-center gap-1">
                            <Zap size={11} />
                            Score: {(provider.score * 100).toFixed(0)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock size={11} />
                            {provider.endpointCount} endpoint{provider.endpointCount !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 ml-3">
                        <span className={cn('w-2 h-2 rounded-full', statusColor(healthStatus))} />
                        <span className="text-jarvis-text-dim/50">
                          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </span>
                      </div>
                    </div>

                    {/* Score bar */}
                    <div className="h-1 bg-jarvis-bg-3/60 rounded-full overflow-hidden">
                      <m.div
                        className="h-full rounded-full bg-gradient-to-r from-jarvis-cyan to-jarvis-blue"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(provider.score * 100, 100)}%` }}
                        transition={{ duration: 0.6, ease: 'easeOut' }}
                      />
                    </div>

                    {/* Expanded detail */}
                    {isExpanded && (
                      <m.div
                        className="mt-4 pt-4 border-t border-jarvis-border/50 space-y-4"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.2 }}
                      >
                        {/* API Caller */}
                        <div>
                          <p className="text-jarvis-text-dim text-[10px] font-mono uppercase tracking-wider mb-2 flex items-center gap-1">
                            <Play size={11} /> Test Endpoint
                          </p>
                          <ApiCaller
                            providerName={provider.name}
                          />
                        </div>

                        {/* Health info */}
                        <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                          <div className="p-2.5 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                            <p className="text-jarvis-text-dim text-[10px] mb-0.5 flex items-center gap-1">
                              <Shield size={11} /> Status
                            </p>
                            <p className="capitalize">{healthStatus}</p>
                          </div>
                          <div className="p-2.5 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
                            <p className="text-jarvis-text-dim text-[10px] mb-0.5 flex items-center gap-1">
                              <ExternalLink size={11} /> Endpoints
                            </p>
                            <p>{provider.endpointCount} registered</p>
                          </div>
                        </div>
                      </m.div>
                    )}
                  </GlassPanel>
                </m.div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

function ApiCaller({ providerName }: { providerName: string; onResult?: (result: ApiCallResponse) => void }) {
  const callMut = useMutation({
    mutationFn: (params: { endpoint: string; queryParams?: Record<string, string> }) =>
      apiClient.post<ApiCallResponse>('/external-apis/call', {
        endpoint: params.endpoint,
        queryParams: params.queryParams,
        task: `Call ${params.endpoint}`,
      }),
  });

  const [endpointInput, setEndpointInput] = useState('');
  const [paramInput, setParamInput] = useState('');

  const handleCall = () => {
    if (!endpointInput.trim()) return;
    const queryParams: Record<string, string> = {};
    if (paramInput.trim()) {
      try {
        const parsed = JSON.parse(paramInput);
        Object.assign(queryParams, parsed);
      } catch {
        queryParams.q = paramInput.trim();
      }
    }
    callMut.mutate({ endpoint: endpointInput.trim(), queryParams });
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <input
          type="text"
          value={endpointInput}
          onChange={(e) => setEndpointInput(e.target.value)}
          placeholder={`e.g. ${providerName.toLowerCase()}_price`}
          className="flex-1 bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-bright placeholder-jarvis-text-dim/50 focus:outline-none focus:border-jarvis-cyan/60"
        />
        <CockpitButton
          variant="glow"
          size="sm"
          icon={<Play size={12} />}
          loading={callMut.isPending}
          onClick={handleCall}
          disabled={!endpointInput.trim()}
        >
          Call
        </CockpitButton>
      </div>
      <input
        type="text"
        value={paramInput}
        onChange={(e) => setParamInput(e.target.value)}
        placeholder="Query params (JSON or text) — optional"
        className="w-full bg-jarvis-bg border border-jarvis-border rounded px-3 py-1.5 text-xs font-mono text-jarvis-text-dim/70 placeholder-jarvis-text-dim/30 focus:outline-none focus:border-jarvis-cyan/60"
      />

      {callMut.data && (
        <m.div
          className="bg-jarvis-bg-2/60 border border-jarvis-border/30 rounded p-3"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
        >
          <div className="flex items-center gap-2 mb-2">
            <span className={callMut.data.success ? 'text-jarvis-green' : 'text-jarvis-red'}>
              {callMut.data.success ? '✓ Success' : '✗ Failed'}
            </span>
            {callMut.data.latencyMs && (
              <span className="text-jarvis-text-dim/50 text-[10px]">{callMut.data.latencyMs.toFixed(0)}ms</span>
            )}
          </div>
          <pre className="text-jarvis-text-bright text-[11px] font-mono whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
            {JSON.stringify(callMut.data.data ?? callMut.data.error, null, 2)}
          </pre>
        </m.div>
      )}
    </div>
  );
}
