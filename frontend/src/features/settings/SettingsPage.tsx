import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { env } from '@/lib/config/env';

export function SettingsPage() {
  const bootstrap = useBootstrapStore((s) => s.data);
  const system = bootstrap?.system;
  const features = bootstrap?.features;
  const voice = bootstrap?.voice;

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Settings" subtitle="System configuration and feature flags" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        {/* System info */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">System</p>
          <dl className="space-y-2 text-xs font-mono">
            <InfoRow label="App" value={system?.appName ?? '—'} />
            <InfoRow label="Version" value={system?.version ?? '—'} />
            <InfoRow label="API Version" value={system?.apiVersion ?? '—'} />
            <InfoRow label="Env" value={system?.appEnv ?? '—'} />
            <InfoRow label="Uptime" value={system?.uptime ?? '—'} />
            <InfoRow label="Status" value={system?.status ?? '—'} highlight />
          </dl>
        </GlassPanel>

        {/* Client info */}
        <GlassPanel className="p-5">
          <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Frontend</p>
          <dl className="space-y-2 text-xs font-mono">
            <InfoRow label="App version" value={env.appVersion} />
            <InfoRow label="Client version" value={env.clientVersion} />
            <InfoRow label="API base" value={env.apiBaseUrl} />
            <InfoRow label="WS base" value={env.wsBaseUrl} />
            <InfoRow label="GPU UI" value={env.enableGpuUi ? 'enabled' : 'disabled'} />
            <InfoRow label="WebGL visuals" value={env.enableWebglVisuals ? 'enabled' : 'disabled'} />
          </dl>
        </GlassPanel>

        {/* Feature flags */}
        {features && (
          <GlassPanel className="p-5">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Feature Flags</p>
            <div className="grid grid-cols-2 gap-2">
              {(Object.entries(features) as [string, boolean][]).map(([key, val]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${val ? 'bg-jarvis-cyan' : 'bg-jarvis-border'}`} />
                  <span className="text-jarvis-text-dim text-xs font-mono">{camelToLabel(key)}</span>
                </div>
              ))}
            </div>
          </GlassPanel>
        )}

        {/* Voice config */}
        {voice && (
          <GlassPanel className="p-5">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-3">Voice</p>
            <dl className="space-y-2 text-xs font-mono">
              <InfoRow label="STT" value={voice.sttEnabled ? `enabled (${voice.sttEngine})` : 'disabled'} />
              <InfoRow label="TTS" value={voice.ttsEnabled ? `enabled (${voice.ttsEngine})` : 'disabled'} />
              <InfoRow label="STT device" value={voice.sttDeviceMode} />
              <InfoRow label="TTS device" value={voice.ttsDeviceMode} />
            </dl>
          </GlassPanel>
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-start gap-2">
      <dt className="text-jarvis-text-dim w-28 shrink-0">{label}</dt>
      <dd className={highlight ? 'text-jarvis-cyan' : 'text-jarvis-text-bright'}>{value}</dd>
    </div>
  );
}

function camelToLabel(s: string): string {
  return s.replace(/([A-Z])/g, ' $1').replace(/^./, (c) => c.toUpperCase()).trim();
}
