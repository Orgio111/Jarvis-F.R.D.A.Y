import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api/client';
import type { GPUStatus } from '@/lib/api/types';
import { useGpuStore } from './gpuStore';
import { connectSSE } from '@/lib/realtime/sseClient';
import { EventTypes } from '@/lib/realtime/eventTypes';
import type { BackendEvent } from '@/lib/api/types';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { detectCapabilities } from '@/lib/rendering/capabilities';

/** Polls /api/gpu/status and subscribes to GPU SSE stream. */
export function useGpuStatus() {
  const isReady = useBootstrapStore((s) => s.status === 'ready');
  const { setStatus, appendMetrics, setRenderingCapabilities } = useGpuStore();

  // Detect rendering capabilities once
  useEffect(() => {
    detectCapabilities().then(setRenderingCapabilities);
  }, [setRenderingCapabilities]);

  // Poll GPU status every 10 seconds
  const query = useQuery({
    queryKey: ['gpu', 'status'],
    queryFn: async () => {
      const res = await apiClient.get<GPUStatus>('/gpu/status');
      setStatus(res.data);
      return res.data;
    },
    enabled: isReady,
    refetchInterval: 10_000,
    staleTime: 8_000,
  });

  // Subscribe to GPU SSE events for live metrics
  useEffect(() => {
    if (!isReady) return;

    const cleanup = connectSSE('/gpu/events/stream', (event: BackendEvent) => {
      if (event.type === EventTypes.GPU_STATUS_CHANGED) {
        setStatus(event.payload as GPUStatus);
      }
      if (event.type === EventTypes.GPU_METRICS_UPDATE) {
        appendMetrics(event.payload as any);
      }
    });

    return cleanup;
  }, [isReady, setStatus, appendMetrics]);

  return query;
}
