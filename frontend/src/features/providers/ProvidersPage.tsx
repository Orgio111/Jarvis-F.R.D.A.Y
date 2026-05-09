import React from 'react';
import { useProviders } from './useProviders';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import type { ProviderStatus } from '@/lib/api/types';

export function ProvidersPage() {
  const { data: providers = [], isLoading } = useProviders();

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="AI Providers" subtitle="Configured provider status and routing" />

      {isLoading ? (
        <div className="text-jarvis-text-dim text-xs font-mono mt-6">Loading providers…</div>
      ) : providers.length === 0 ? (
        <NoProviders />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
          {providers.map((p) => (
            <ProviderCard key={p.id} provider={p} />
          ))}
        </div>
      )}
    </div>
  );
}

function ProviderCard({ provider }: { provider: ProviderStatus }) {
  const isAvailable = provider.status === 'available';
  const isUnavailable = provider.status === 'provider_unavailable';

  return (
    <GlassPanel className="p-5">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold">{provider.name}</p>
          <p className="text-jarvis-text-dim text-xs font-mono mt-0.5">{provider.id}</p>
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
    </GlassPanel>
  );
}

function NoProviders() {
  return (
    <GlassPanel className="p-8 text-center mt-6 max-w-md">
      <p className="text-jarvis-text-dim text-sm font-mono">
        No providers configured.
      </p>
      <p className="text-jarvis-text-dim text-xs font-mono mt-2">
        Add <code className="text-jarvis-cyan">NVIDIA_NIM_API_KEY</code> or{' '}
        <code className="text-jarvis-cyan">OPENROUTER_API_KEY</code> to your{' '}
        <code className="text-jarvis-cyan">.env</code> file.
      </p>
    </GlassPanel>
  );
}
