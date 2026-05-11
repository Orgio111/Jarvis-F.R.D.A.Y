import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import type { Model } from '@/lib/api/types';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface ModelsResponse {
  models: Model[];
  total: number;
}

export function useModels(providerId?: string) {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');
  const queryKey = providerId ? ['models', providerId] : ['models'];
  const path = providerId ? `/models?provider=${providerId}` : '/models';

  return useQuery<ModelsResponse>({
    queryKey,
    queryFn: async () => {
      const res = await apiClient.get<ModelsResponse>(path);
      return res ?? { models: [], total: 0 };
    },
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });
}
