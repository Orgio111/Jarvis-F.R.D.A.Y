/**
 * Bootstrap hook.
 * Implements bootstrap-first startup: fetches /api/bootstrap and hydrates all stores.
 * Retries with exponential backoff on failure.
 * No other feature endpoint is called before bootstrap succeeds.
 */

import { useEffect, useRef } from 'react';
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
  const { status, retryCount, setLoading, setReady, setError } = useBootstrapStore();
  const abortRef = useRef<AbortController | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (status === 'ready') return;

    async function fetchBootstrap() {
      setLoading();
      abortRef.current = new AbortController();

      try {
        const result = await apiClient.get<BootstrapData>('/bootstrap', {
          signal: abortRef.current.signal,
        });

        // Hydrate all feature stores from bootstrap data
        hydrateStores(result);
        setReady(result);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError(getErrorMessage(err));

        // Schedule retry with backoff
        if (retryCount < MAX_RETRIES) {
          const delay = backoffDelay(retryCount);
          timerRef.current = setTimeout(fetchBootstrap, delay);
        }
      }
    }

    fetchBootstrap();

    return () => {
      abortRef.current?.abort();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [retryCount]); // re-run when retryCount changes (after error)

  return { status, retryCount };
}

function hydrateStores(data: BootstrapData): void {
  // Hydrate GPU store
  useGpuStore.getState().setStatus(data.gpu);
}
