import { create } from 'zustand';
import type { BootstrapData } from '@/lib/api/types';

export type BootstrapStatus = 'idle' | 'loading' | 'ready' | 'error';

interface BootstrapState {
  status: BootstrapStatus;
  data: BootstrapData | null;
  error: string | null;
  retryCount: number;
  lastBootstrappedAt: string | null;
  /** Increments each time reset() is called so useBootstrap's effect can re-trigger. */
  resetKey: number;

  setLoading: () => void;
  setReady: (_data: BootstrapData) => void;
  setError: (_message: string) => void;
  incrementRetry: () => void;
  reset: () => void;
}

export const useBootstrapStore = create<BootstrapState>((set) => ({
  status: 'idle',
  data: null,
  error: null,
  retryCount: 0,
  lastBootstrappedAt: null,
  resetKey: 0,

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
    set({ status: 'error', error: message }),

  incrementRetry: () => set((state) => ({ retryCount: state.retryCount + 1 })),

  reset: () =>
    set((state) => ({
      status: 'idle',
      data: null,
      error: null,
      retryCount: 0,
      lastBootstrappedAt: null,
      resetKey: state.resetKey + 1,
    })),
}));

// ─── Typed selectors ──────────────────────────────────────────────────────────
export const selectBootstrapReady = (s: BootstrapState) => s.status === 'ready';
export const selectBootstrapData = (s: BootstrapState) => s.data;
export const selectGPUStatus = (s: BootstrapState) => s.data?.gpu ?? null;
export const selectProviders = (s: BootstrapState) => s.data?.providers ?? null;
export const selectFeatures = (s: BootstrapState) => s.data?.features ?? null;
export const selectSystemInfo = (s: BootstrapState) => s.data?.system ?? null;
