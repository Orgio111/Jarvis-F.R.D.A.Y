import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type { ProviderStatus } from '@/lib/api/types';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

export function useProviders() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  return useQuery<ProviderStatus[]>({
    queryKey: ['providers'],
    queryFn: async () => {
      const res = await apiClient.get<ProviderStatus[]>('/providers');
      return Array.isArray(res) ? res : [];
    },
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });
}

/** Fetch discovered providers separately */
export function useDiscoveredProviders() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  const query = useQuery<ProviderStatus[]>({
    queryKey: ['providers', 'discovered'],
    queryFn: async () => {
      const res = await apiClient.get<ProviderStatus[]>('/providers/discovered');
      return Array.isArray(res) ? res : [];
    },
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });

  const queryClient = useQueryClient();

  const syncMutation = useMutation({
    mutationFn: async () => {
      return apiClient.post<{ synced: number }>('/providers/discover/sync');
    },
    onSuccess: () => {
      // Invalidate both queries to refresh the lists
      queryClient.invalidateQueries({ queryKey: ['providers'] });
      queryClient.invalidateQueries({ queryKey: ['providers', 'discovered'] });
    },
  });

  return {
    discovered: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    isSyncing: syncMutation.isPending,
    sync: syncMutation.mutate,
    syncError: syncMutation.error,
  };
}
