import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

interface SystemMetric {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  uptime_seconds: number;
}

interface GpuMetric {
  name: string;
  utilization_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  temperature_c: number;
  power_draw_w: number;
}

interface MonitoringData {
  system: SystemMetric;
  gpus: GpuMetric[];
  timestamp: number;
}

function Bar({ value, color = 'bg-jarvis-cyan' }: { value: number; color?: string }) {
  const pct = Math.min(100, Math.max(0, value));
  const danger = pct > 85;
  const warn = pct > 70;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-jarvis-bg rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${danger ? 'bg-jarvis-red' : warn ? 'bg-yellow-500' : color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-mono w-10 text-right ${danger ? 'text-jarvis-red' : 'text-jarvis-text-dim'}`}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

function formatUptime(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

export function MonitoringPage() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  const { data, isError } = useQuery<MonitoringData>({
    queryKey: ['monitoring-metrics'],
    queryFn: () => apiClient.get<MonitoringData>('/monitoring/metrics'),
    enabled: bootstrapReady,
    refetchInterval: 5000,
    staleTime: 4000,
  });

  const sys = data?.system;

  return (
    <div className="p-6 overflow-auto h-full">
      <SectionHeader title="Monitoring" subtitle="Live system and GPU metrics — refreshes every 5s" />

      {isError && (
        <GlassPanel className="p-4 mt-6">
          <p className="text-jarvis-red text-xs font-mono">Could not fetch metrics. Is the AI service running?</p>
        </GlassPanel>
      )}

      {sys && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* CPU & Memory */}
          <GlassPanel className="p-5">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-4">System</p>
            <div className="space-y-3">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-jarvis-text-dim text-xs font-mono">CPU</span>
                </div>
                <Bar value={sys.cpu_percent} />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-jarvis-text-dim text-xs font-mono">Memory</span>
                  <span className="text-jarvis-text-dim text-xs font-mono">
                    {sys.memory_used_gb.toFixed(1)} / {sys.memory_total_gb.toFixed(1)} GB
                  </span>
                </div>
                <Bar value={sys.memory_percent} color="bg-jarvis-blue" />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-jarvis-text-dim text-xs font-mono">Disk</span>
                  <span className="text-jarvis-text-dim text-xs font-mono">
                    {sys.disk_used_gb.toFixed(1)} / {sys.disk_total_gb.toFixed(1)} GB
                  </span>
                </div>
                <Bar value={sys.disk_percent} color="bg-green-500" />
              </div>
              <div className="pt-2 border-t border-jarvis-border">
                <span className="text-jarvis-text-dim text-xs font-mono">
                  Uptime: {formatUptime(sys.uptime_seconds)}
                </span>
              </div>
            </div>
          </GlassPanel>

          {/* GPU(s) */}
          <GlassPanel className="p-5">
            <p className="text-jarvis-text-bright text-sm font-mono font-semibold mb-4">GPU</p>
            {data?.gpus && data.gpus.length > 0 ? (
              <div className="space-y-4">
                {data.gpus.map((gpu, i) => (
                  <div key={i}>
                    <p className="text-jarvis-text-bright text-xs font-mono mb-2 truncate">{gpu.name}</p>
                    <div className="space-y-2">
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-jarvis-text-dim text-xs font-mono">Utilization</span>
                        </div>
                        <Bar value={gpu.utilization_percent} color="bg-jarvis-cyan" />
                      </div>
                      <div>
                        <div className="flex justify-between mb-1">
                          <span className="text-jarvis-text-dim text-xs font-mono">VRAM</span>
                          <span className="text-jarvis-text-dim text-xs font-mono">
                            {(gpu.memory_used_mb / 1024).toFixed(1)} / {(gpu.memory_total_mb / 1024).toFixed(1)} GB
                          </span>
                        </div>
                        <Bar value={(gpu.memory_used_mb / gpu.memory_total_mb) * 100} color="bg-jarvis-blue" />
                      </div>
                      <div className="flex gap-4 pt-1">
                        <span className="text-jarvis-text-dim text-xs font-mono">{gpu.temperature_c}°C</span>
                        <span className="text-jarvis-text-dim text-xs font-mono">{gpu.power_draw_w.toFixed(0)} W</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <StatusDot status="offline" label="no GPU detected" />
              </div>
            )}
          </GlassPanel>
        </div>
      )}

      {!data && !isError && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          {[0, 1].map((i) => (
            <GlassPanel key={i} className="p-5 animate-pulse">
              <div className="h-4 w-24 bg-jarvis-border rounded mb-4" />
              <div className="space-y-3">
                {[0, 1, 2].map((j) => (
                  <div key={j} className="h-2 w-full bg-jarvis-border rounded" />
                ))}
              </div>
            </GlassPanel>
          ))}
        </div>
      )}
    </div>
  );
}
