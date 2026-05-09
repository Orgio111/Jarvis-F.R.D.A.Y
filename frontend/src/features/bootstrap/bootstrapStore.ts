import { create } from 'zustand';
import type { BootstrapData } from '@/lib/api/types';

export type BootstrapStatus = 'idle' | 'loading' | 'ready' | 'error';

interface BootstrapState {
  status: BootstrapStatus;
  data: BootstrapData | null;
  error: string | null;
  retryCount: number;
  lastBootstrappedAt: string | null;

  setLoading: () => void;
  setReady: (data: BootstrapData) => void;
  setError: (message: string) => void;
  incrementRetry: () => void;
  reset: () => void;
}

export const useBootstrapStore = create<BootstrapState>((set, get) => ({
  status: 'idle',
  data: null,
  error: null,
  retryCount: 0,
  lastBootstrappedAt: null,

  setLoading: () => set({ status: 'loading', error: null }),

  setReady: (data) =>
    set({
      status: 'ready',
      data,
      error: null,
      retryCount: 0,
      lastBootstrappedAt: new Date().toISOString(),
    }),

  setError: (message) =>
    set((state) => ({ status: 'error', error: message, retryCount: state.retryCount + 1 })),

  incrementRetry: () => set((state) => ({ retryCount: state.retryCount + 1 })),

  reset: () =>
    set({ status: 'idle', data: null, error: null, retryCount: 0, lastBootstrappedAt: null }),
}));

// ─── Typed selectors ──────────────────────────────────────────────────────────
export const selectBootstrapReady = (s: BootstrapState) => s.status === 'ready';
export const selectBootstrapData = (s: BootstrapState) => s.data;
export const selectGPUStatus = (s: BootstrapState) => s.data?.gpu ?? null;
export const selectProviders = (s: BootstrapState) => s.data?.providers ?? null;
export const selectFeatures = (s: BootstrapState) => s.data?.features ?? null;
export const selectSystemInfo = (s: BootstrapState) => s.data?.system ?? null;
