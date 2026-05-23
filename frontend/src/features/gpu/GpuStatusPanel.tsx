import { m } from 'framer-motion';
import { Cpu, Thermometer, Zap, Activity, HardDrive, CircuitBoard, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { useGpuStore } from './gpuStore';
import { useGpuStatus } from './useGpuStatus';
import { GpuWorkloadsPanel } from './GpuWorkloadsPanel';
import { GpuMetricsChart } from './GpuMetricsChart';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { SectionHeader } from '@/components/ui/SectionHeader';

export function GpuStatusPanel() {
  const { isLoading } = useGpuStatus();
  const status = useGpuStore((s) => s.status);
  const renderCaps = useGpuStore((s) => s.renderingCapabilities);

  if (!status) {
    return (
      <div className="p-4">
        <GlassPanel className="p-8 flex items-center justify-center">
          <div className="text-center">
            <Cpu size={32} className="mx-auto mb-3 text-jarvis-text-dim/30" />
            <p className="text-jarvis-text-dim text-sm font-mono">
              {isLoading ? 'Loading GPU status...' : 'No GPU status available'}
            </p>
          </div>
        </GlassPanel>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <m.div
        className="flex items-center justify-between"
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-jarvis-purple/10 border border-jarvis-purple/30 flex items-center justify-center">
            <Cpu size={16} className="text-jarvis-purple" />
          </div>
          <div>
            <h2 className="text-jarvis-text-bright text-sm font-mono font-semibold tracking-wide">
              GPU / Compute
            </h2>
            <p className="text-jarvis-text-dim text-[10px] font-mono">Hardware acceleration status</p>
          </div>
        </div>
        <NeonBadge
          color={status.available ? 'green' : status.fallback.cpuFallbackActive ? 'yellow' : 'dim'}
          label={status.available ? 'ACTIVE' : status.fallback.cpuFallbackActive ? 'CPU MODE' : 'DISABLED'}
          pulse={status.available}
        />
      </m.div>

      {/* Device info */}
      <GlassPanel className="p-5" hover glow>
        <div className="grid grid-cols-2 gap-4">
          <InfoRow icon={<CircuitBoard size={14} />} label="Device" value={status.activeDevice} />
          <InfoRow icon={<Zap size={14} />} label="Provider" value={status.provider.toUpperCase()} />
          <InfoRow icon={<CheckCircle2 size={14} />} label="CUDA" value={status.cudaAvailable ? status.cudaVersion ?? 'Available' : 'N/A'} />
          <InfoRow icon={<Activity size={14} />} label="Driver" value={status.driverVersion ?? 'N/A'} />
        </div>
      </GlassPanel>

      {/* Utilization */}
      {status.available && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <GlassPanel className="p-5" hover>
            <SectionHeader title="Utilization" />
            <div className="space-y-3">
              <UtilBar label="GPU" pct={status.utilization.gpuPercent} color="text-jarvis-cyan" barColor="bg-jarvis-cyan" />
              <UtilBar label="Memory" pct={status.utilization.memoryPercent} color="text-jarvis-blue" barColor="bg-jarvis-blue" />
              <div className="flex justify-between text-xs font-mono text-jarvis-text-dim/70 pt-2 border-t border-jarvis-border/20">
                <span className="flex items-center gap-1">
                  <Thermometer size={12} />
                  {status.utilization.temperatureC.toFixed(0)}°C
                </span>
                <span className="flex items-center gap-1">
                  <Zap size={12} />
                  {status.utilization.powerWatts.toFixed(0)}W
                </span>
              </div>
            </div>
          </GlassPanel>

          <GlassPanel className="p-5" hover>
            <SectionHeader title="VRAM" subtitle={`${(status.vram.usedMb / 1024).toFixed(1)} / ${(status.vram.totalMb / 1024).toFixed(1)} GB`} />
            <VRAMBar used={status.vram.usedMb} total={status.vram.totalMb} />
          </GlassPanel>
        </div>
      )}

      {!status.available && (
        <GlassPanel className="p-5">
          <div className="flex items-start gap-3 p-4 rounded-xl bg-jarvis-yellow/5 border border-jarvis-yellow/20">
            <AlertTriangle size={18} className="text-jarvis-yellow shrink-0 mt-0.5" />
            <div>
              <p className="text-jarvis-text-bright text-sm font-mono mb-1">CPU Fallback Mode</p>
              <p className="text-jarvis-text-dim text-xs font-mono">
                {status.fallback.reason ?? 'GPU not available'}
              </p>
            </div>
          </div>
        </GlassPanel>
      )}

      {/* Workloads */}
      {(() => {
        const wl = status.workloads;
        if (!wl) return null;
        const hasActive = Object.values(wl).some((v) => v !== 'disabled');
        return hasActive ? <GpuWorkloadsPanel workloads={wl} /> : null;
      })()}

      {/* Metrics chart */}
      {status.available && <GpuMetricsChart />}

      {/* Rendering capabilities */}
      {renderCaps && (
        <GlassPanel className="p-5" glow>
          <div className="flex items-center gap-2 mb-3">
            <Activity size={14} className="text-jarvis-text-dim" />
            <span className="text-jarvis-text-dim text-xs font-mono">Client GPU Rendering</span>
          </div>
          <div className="flex gap-2 flex-wrap">
            <CapBadge label="WebGL2" available={renderCaps.webgl2} />
            <CapBadge label="WebGPU" available={renderCaps.webgpu} />
            <CapBadge label={`${renderCaps.hardwareConcurrency} cores`} available={true} />
            {renderCaps.deviceMemoryGB && (
              <CapBadge label={`${renderCaps.deviceMemoryGB}GB RAM`} available={true} />
            )}
          </div>
          {renderCaps.renderer !== 'unknown' && (
            <p className="text-jarvis-text-dim text-[10px] mt-2 font-mono opacity-60 truncate">
              {renderCaps.renderer}
            </p>
          )}
        </GlassPanel>
      )}
    </div>
  );
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-jarvis-bg-2/40 border border-jarvis-border/20">
      <span className="text-jarvis-text-dim/60">{icon}</span>
      <div>
        <p className="text-jarvis-text-dim text-[10px] font-mono">{label}</p>
        <p className="text-jarvis-text text-xs font-mono truncate">{value}</p>
      </div>
    </div>
  );
}

function VRAMBar({ used, total }: { used: number; total: number }) {
  const pct = total > 0 ? (used / total) * 100 : 0;
  const color = pct > 85 ? 'bg-jarvis-red' : pct > 60 ? 'bg-jarvis-yellow' : 'bg-jarvis-cyan';
  return (
    <div>
      <div className="flex justify-between text-xs font-mono text-jarvis-text-dim mb-1.5">
        <span className="flex items-center gap-1.5">
          <HardDrive size={12} />
          VRAM
        </span>
        <span>{Math.round(pct)}%</span>
      </div>
      <div className="h-2 bg-jarvis-bg-3/50 rounded-full overflow-hidden">
        <m.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

function UtilBar({ label, pct, color, barColor }: { label: string; pct: number; color: string; barColor: string }) {
  return (
    <div>
      <div className="flex justify-between text-xs font-mono text-jarvis-text-dim mb-1">
        <span>{label}</span>
        <span className={color}>{Math.round(pct)}%</span>
      </div>
      <div className="h-1.5 bg-jarvis-bg-3/50 rounded-full overflow-hidden">
        <m.div
          className={`h-full rounded-full ${barColor}`}
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
      className={`text-xs font-mono px-2.5 py-1 rounded-lg border transition-all duration-200 ${
        available
          ? 'border-jarvis-green/30 text-jarvis-green bg-jarvis-green/5'
          : 'border-jarvis-border/20 text-jarvis-text-dim/40 bg-jarvis-bg-2/30'
      }`}
    >
      {label}
    </span>
  );
}
