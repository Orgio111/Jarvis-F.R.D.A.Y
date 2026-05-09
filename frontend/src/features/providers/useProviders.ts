import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type { ProviderStatus } from '@/lib/api/types';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';

interface ProvidersResponse {
  providers: ProviderStatus[];
}

export function useProviders() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  return useQuery<ProviderStatus[]>({
    queryKey: ['providers'],
    queryFn: async () => {
      const res = await apiClient.get<ProviderStatus[]>('/providers');
      return Array.isArray(res) ? res : [];
    },
    enabled: bootstrapReady,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
