import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface ExternalApiProvider {
  name: string;
  description: string;
  status: 'unknown' | 'online' | 'degraded' | 'offline';
  endpointCount: number;
  tags: string[];
  score: number;
}

interface ApiCallResponse {
  success: boolean;
  data?: unknown;
  error?: string;
  provider?: string;
  latencyMs?: number;
  endpoint?: string;
}

export function useExternalApiProviders() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  return useQuery<ExternalApiProvider[]>({
    queryKey: ['external-apis', 'providers'],
    queryFn: () => apiClient.get<ExternalApiProvider[]>('/external-apis/providers'),
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });
}

export function useExternalApiHealth() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  return useQuery<Record<string, string>>({
    queryKey: ['external-apis', 'health'],
    queryFn: () => apiClient.get<Record<string, string>>('/external-apis/health'),
    enabled: bootstrapReady,
    ...freshness.resourceState,
  });
}

export function useExternalApiCall() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { endpoint: string; queryParams?: Record<string, string>; authToken?: string }) =>
      apiClient.post<ApiCallResponse>('/external-apis/call', params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['external-apis'] });
    },
  });
}
