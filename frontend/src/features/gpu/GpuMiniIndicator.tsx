import React from 'react';
import { motion } from 'framer-motion';
import { useGpuStore } from './gpuStore';

/**
 * Compact GPU status badge shown in the TopStatusBar.
 */
export function GpuMiniIndicator() {
  const status = useGpuStore((s) => s.status);

  if (!status) return null;

  const isAvailable = status.available;
  const isCpuFallback = status.fallback.cpuFallbackActive;
  const utilPct = status.utilization.gpuPercent;

  const color = isAvailable
    ? utilPct > 80
      ? 'text-jarvis-red'
      : utilPct > 50
      ? 'text-jarvis-yellow'
      : 'text-jarvis-green'
    : 'text-jarvis-text-dim';

  const label = isAvailable
    ? `GPU ${Math.round(utilPct)}%`
    : isCpuFallback
    ? 'CPU mode'
    : 'GPU off';

  return (
    <motion.div
      className="flex items-center gap-1.5 px-2 py-1 rounded border border-jarvis-border"
      whileHover={{ borderColor: 'rgba(0, 212, 255, 0.45)' }}
      title={
        isAvailable
          ? `${status.activeDevice}\nVRAM: ${status.vram.usedMb}/${status.vram.totalMb} MB`
          : status.fallback.reason ?? 'GPU not available'
      }
    >
      {/* Status dot */}
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isAvailable ? 'bg-jarvis-green animate-pulse' : 'bg-jarvis-text-dim'
        }`}
      />
      <span className={`text-xs font-mono ${color}`}>{label}</span>
    </motion.div>
  );
}
