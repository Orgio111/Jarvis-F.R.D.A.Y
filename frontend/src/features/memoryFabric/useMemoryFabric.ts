import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { freshness } from '@/lib/query/freshness';

export interface MemoryEntry {
  entryId: string;
  layer: string;
  content: string;
  tags: string[];
  source: string;
  importance: number;
  confidence: number;
  timestamp: number;
  ageSeconds: number;
  accessCount: number;
  relevanceScore: number;
  metadata: Record<string, string>;
}

export interface MemoryFabricStats {
  totalEntries: number;
  entriesByLayer: Record<string, number>;
  avgImportance: number;
  avgConfidence: number;
  uniqueTags: number;
}

export function useMemoryFabricStatus() {
  return useQuery<{ initialized: boolean; layers: string[]; totalEntries: number }>({
    queryKey: ['memory-fabric', 'status'],
    queryFn: () => apiClient.get('/memory-fabric/status'),
    staleTime: freshness.slowlyChanging.staleTime,
    gcTime: freshness.slowlyChanging.gcTime,
  });
}

export function useMemoryFabricStats() {
  return useQuery<MemoryFabricStats>({
    queryKey: ['memory-fabric', 'stats'],
    queryFn: () => apiClient.get('/memory-fabric/stats'),
    staleTime: freshness.resourceState.staleTime,
    gcTime: freshness.resourceState.gcTime,
  });
}

export function useSearchMemory() {
  return useMutation({
    mutationFn: (params: { query: string; layer?: string; limit?: number }) => {
      const searchParams = new URLSearchParams();
      searchParams.set('q', params.query);
      if (params.layer) searchParams.set('layer', params.layer);
      if (params.limit) searchParams.set('limit', params.limit.toString());
      return apiClient.get(`/memory-fabric/search?${searchParams.toString()}`);
    },
  });
}

export function useStoreMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { content: string; layer?: string; tags?: string; source?: string; importance?: number }) =>
      apiClient.post('/memory-fabric/store', params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memory-fabric', 'stats'] });
      qc.invalidateQueries({ queryKey: ['memory-fabric', 'status'] });
    },
  });
}

export function useRecentMemories(layer?: string, limit?: number) {
  const searchParams = new URLSearchParams();
  if (layer) searchParams.set('layer', layer);
  if (limit) searchParams.set('limit', limit.toString());

  return useQuery<{ results: MemoryEntry[] }>({
    queryKey: ['memory-fabric', 'recent', layer, limit],
    queryFn: () => apiClient.get(`/memory-fabric/recent?${searchParams.toString()}`),
    staleTime: freshness.resourceState.staleTime,
    gcTime: freshness.resourceState.gcTime,
  });
}

export function usePruneMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>      apiClient.post('/memory-fabric/prune', undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['memory-fabric', 'stats'] });
      qc.invalidateQueries({ queryKey: ['memory-fabric', 'recent'] });
    },
  });
}

export function useCrossLayerQuery() {
  return useMutation({
    mutationFn: (topic: string) => {
      const params = new URLSearchParams();
      params.set('topic', topic);
      params.set('per_layer', '5');
      return apiClient.get(`/memory-fabric/cross-layer?${params.toString()}`);
    },
  });
}
