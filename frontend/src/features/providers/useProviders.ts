import { useQuery } from '@tanstack/react-query';
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
