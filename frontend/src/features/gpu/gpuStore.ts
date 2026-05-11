import { create } from 'zustand';
import type { GPUStatus, GPUMetrics } from '@/lib/api/types';
import type { RenderingCapabilities } from '@/lib/rendering/capabilities';

interface GPUStore {
  status: GPUStatus | null;
  metrics: GPUMetrics[];
  renderingCapabilities: RenderingCapabilities | null;
  lastUpdatedAt: string | null;

  setStatus: (_status: GPUStatus) => void;
  appendMetrics: (_metric: GPUMetrics) => void;
  setRenderingCapabilities: (_caps: RenderingCapabilities) => void;
  clear: () => void;
}

const MAX_METRICS_HISTORY = 60; // keep 60 data points

export const useGpuStore = create<GPUStore>((set) => ({
  status: null,
  metrics: [],
  renderingCapabilities: null,
  lastUpdatedAt: null,

  setStatus: (status) =>
    set({ status, lastUpdatedAt: new Date().toISOString() }),

  appendMetrics: (metric) =>
    set((state) => ({
      metrics: [...state.metrics.slice(-MAX_METRICS_HISTORY + 1), metric],
    })),

  setRenderingCapabilities: (renderingCapabilities) =>
    set({ renderingCapabilities }),

  clear: () =>
    set({ status: null, metrics: [], lastUpdatedAt: null }),
}));

// ─── Selectors ────────────────────────────────────────────────────────────────
export const selectGpuAvailable = (s: GPUStore) => s.status?.available ?? false;
export const selectGpuEnabled = (s: GPUStore) => s.status?.enabled ?? false;
export const selectCpuFallbackActive = (s: GPUStore) => s.status?.fallback.cpuFallbackActive ?? true;
export const selectWorkloads = (s: GPUStore) => s.status?.workloads ?? null;
export const selectUtilization = (s: GPUStore) => s.status?.utilization ?? null;
export const selectVram = (s: GPUStore) => s.status?.vram ?? null;
