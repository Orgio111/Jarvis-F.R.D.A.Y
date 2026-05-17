/**
 * Bootstrap hook.
 * Implements bootstrap-first startup: fetches /api/bootstrap and hydrates all stores.
 * Retries with exponential backoff on failure.
 * No other feature endpoint is called before bootstrap succeeds.
 */

import { useEffect } from 'react';
import apiClient from '@/lib/api/client';
import type { BootstrapData } from '@/lib/api/types';
import { useBootstrapStore } from './bootstrapStore';
import { useGpuStore } from '@/features/gpu/gpuStore';
import { getErrorMessage } from '@/lib/api/errors';

const MAX_RETRIES = 8;
const BASE_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;

function backoffDelay(retryCount: number): number {
  return Math.min(BASE_DELAY_MS * Math.pow(2, retryCount), MAX_DELAY_MS);
}

export function useBootstrap() {
  const { status, retryCount, resetKey, setLoading, setReady, setError, incrementRetry } =
    useBootstrapStore();

  useEffect(() => {
    let cancelled = false;
    let abortController: AbortController | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    async function attempt(retryNum: number) {
      if (cancelled) return;

      abortController?.abort();
      abortController = new AbortController();
      setLoading();

      try {
        const result = await apiClient.get<BootstrapData>('/bootstrap', {
          signal: abortController.signal,
        });
        if (cancelled) return;
        hydrateStores(result);
        setReady(result);
      } catch (err) {
        if (cancelled || (err as Error).name === 'AbortError') return;

        setError(getErrorMessage(err));

        if (retryNum < MAX_RETRIES) {
          incrementRetry();
          const delay = backoffDelay(retryNum + 1);
          retryTimer = setTimeout(() => attempt(retryNum + 1), delay);
        }
      }
    }

    attempt(0);

    return () => {
      cancelled = true;
      abortController?.abort();
      if (retryTimer) clearTimeout(retryTimer);
    };
    // Re-run only when resetKey changes (user clicked Retry in RecoveryScreen).
    // Zustand actions are stable and don't need to be deps.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetKey]);

  return { status, retryCount };
}

function hydrateStores(data: BootstrapData): void {
  // Hydrate GPU store (this store is currently the only one with explicit setters)
  useGpuStore.getState().setStatus(data.gpu);

  // Other bootstrap slices (system/providers/features/etc.) are consumed directly
  // from `useBootstrapStore((s) => s.data)` in the UI. No additional Zustand
  // stores exist for those slices in this codebase.
}

