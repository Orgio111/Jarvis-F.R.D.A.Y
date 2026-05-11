import { m } from 'framer-motion';
import { useGpuStore } from './gpuStore';
import { useGpuStatus } from './useGpuStatus';
import { GpuWorkloadsPanel } from './GpuWorkloadsPanel';
import { GpuMetricsChart } from './GpuMetricsChart';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { NeonBadge } from '@/components/ui/NeonBadge';

export function GpuStatusPanel() {
  const { isLoading } = useGpuStatus();
  const status = useGpuStore((s) => s.status);
  const renderCaps = useGpuStore((s) => s.renderingCapabilities);

  if (!status) {
    return (
      <div className="flex items-center justify-center h-48 text-jarvis-text-dim text-sm">
        {isLoading ? 'Loading GPU status...' : 'No GPU status available'}
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-jarvis-text-bright text-base font-semibold tracking-wide">
          GPU / Compute
        </h2>
        <NeonBadge
          color={status.available ? 'green' : 'dim'}
          label={status.available ? 'ACTIVE' : status.fallback.cpuFallbackActive ? 'CPU MODE' : 'DISABLED'}
        />
      </div>

      {/* Device info */}
      <GlassPanel className="p-4">
        <div className="grid grid-cols-2 gap-4">
          <InfoRow label="Device" value={status.activeDevice} />
          <InfoRow label="Provider" value={status.provider.toUpperCase()} />
          <InfoRow label="CUDA" value={status.cudaAvailable ? status.cudaVersion ?? 'Available' : 'N/A'} />
          <InfoRow label="Driver" value={status.driverVersion ?? 'N/A'} />
        </div>

        {status.available && (
          <div className="mt-4 space-y-2">
            <VRAMBar used={status.vram.usedMb} total={status.vram.totalMb} />
            <UtilBar label="GPU" pct={status.utilization.gpuPercent} />
            <div className="flex justify-between text-xs font-mono text-jarvis-text-dim">
              <span>Temp: {status.utilization.temperatureC.toFixed(0)}°C</span>
              <span>Power: {status.utilization.powerWatts.toFixed(0)}W</span>
            </div>
          </div>
        )}

        {!status.available && (
          <div className="mt-4 p-3 rounded border border-jarvis-border bg-jarvis-bg-2">
            <p className="text-jarvis-text-dim text-xs font-mono">
              {status.fallback.reason ?? 'GPU not available'}
            </p>
            <p className="text-jarvis-cyan text-xs mt-1">
              Running in CPU fallback mode
            </p>
          </div>
        )}
      </GlassPanel>

      {/* Workloads */}
      <GpuWorkloadsPanel workloads={status.workloads} />

      {/* Metrics chart */}
      {status.available && <GpuMetricsChart />}

      {/* Rendering capabilities */}
      {renderCaps && (
        <GlassPanel className="p-4">
          <p className="text-jarvis-text-dim text-xs font-mono mb-3">Client GPU Rendering</p>
          <div className="flex gap-3 flex-wrap">
            <CapBadge label="WebGL2" available={renderCaps.webgl2} />
            <CapBadge label="WebGPU" available={renderCaps.webgpu} />
            <CapBadge label={`${renderCaps.hardwareConcurrency} cores`} available={true} />
            {renderCaps.deviceMemoryGB && (
              <CapBadge label={`${renderCaps.deviceMemoryGB}GB RAM`} available={true} />
            )}
          </div>
          {renderCaps.renderer !== 'unknown' && (
            <p className="text-jarvis-text-dim text-xs mt-2 font-mono truncate">
              {renderCaps.renderer}
            </p>
          )}
        </GlassPanel>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-jarvis-text-dim text-xs mb-0.5">{label}</p>
      <p className="text-jarvis-text text-xs font-mono truncate">{value}</p>
    </div>
  );
}

function VRAMBar({ used, total }: { used: number; total: number }) {
  const pct = total > 0 ? (used / total) * 100 : 0;
  const color = pct > 85 ? 'bg-jarvis-red' : pct > 60 ? 'bg-jarvis-yellow' : 'bg-jarvis-cyan';
  return (
    <div>
      <div className="flex justify-between text-xs font-mono text-jarvis-text-dim mb-1">
        <span>VRAM</span>
        <span>{used} / {total} MB ({Math.round(pct)}%)</span>
      </div>
      <div className="h-1.5 bg-jarvis-bg-3 rounded-full overflow-hidden">
        <m.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

function UtilBar({ label, pct }: { label: string; pct: number }) {
  const color = pct > 85 ? 'bg-jarvis-red' : pct > 50 ? 'bg-jarvis-yellow' : 'bg-jarvis-green';
  return (
    <div>
      <div className="flex justify-between text-xs font-mono text-jarvis-text-dim mb-1">
        <span>{label} Util</span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div className="h-1.5 bg-jarvis-bg-3 rounded-full overflow-hidden">
        <m.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

function CapBadge({ label, available }: { label: string; available: boolean }) {
  return (
    <span
      className={`text-xs font-mono px-2 py-0.5 rounded border ${
        available
          ? 'border-jarvis-green text-jarvis-green'
          : 'border-jarvis-border text-jarvis-text-dim'
      }`}
    >
      {label}
    </span>
  );
}
