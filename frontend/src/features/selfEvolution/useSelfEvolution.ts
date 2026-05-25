import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { freshness } from '@/lib/query/freshness';

export interface EvolutionTrial {
  trialId: string;
  mutationType: string;
  target: string;
  originalScore?: { composite: number; [key: string]: number };
  mutatedScore?: { composite: number; [key: string]: number };
  improved: boolean;
  improvementDelta: number;
  timestamp: number;
}

export interface EvolutionStatus {
  totalTrials: number;
  improvedTrials: number;
  improvementRate: number;
  targetsTracked: number;
  mutationSuccessRates: Record<string, number>;
  autoMutateThreshold: number;
}

export interface BestPractice {
  trialId: string;
  mutationType: string;
  target: string;
  improvementDelta: number;
  originalComposite: number;
  mutatedComposite: number;
}

export function useEvolutionStatus() {
  return useQuery<EvolutionStatus>({
    queryKey: ['evolution', 'status'],
    queryFn: () => apiClient.get('/evolution/status'),
    staleTime: freshness.slowlyChanging.staleTime,
    gcTime: freshness.slowlyChanging.gcTime,
  });
}

export function useEvolutionTrials(limit?: number) {
  const params = limit ? `?limit=${limit}` : '';
  return useQuery<{ trials: EvolutionTrial[] }>({
    queryKey: ['evolution', 'trials', limit],
    queryFn: () => apiClient.get(`/evolution/trials${params}`),
    staleTime: freshness.resourceState.staleTime,
    gcTime: freshness.resourceState.gcTime,
  });
}

export function useBestPractices(limit?: number) {
  const params = limit ? `?limit=${limit}` : '';
  return useQuery<{ bestPractices: BestPractice[] }>({
    queryKey: ['evolution', 'best-practices', limit],
    queryFn: () => apiClient.get(`/evolution/best-practices${params}`),
    staleTime: freshness.slowlyChanging.staleTime,
    gcTime: freshness.slowlyChanging.gcTime,
  });
}

export function useProposeMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { mutationType: string; target: string; currentValue: unknown }) =>
      apiClient.post('/evolution/propose', params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['evolution', 'trials'] });
    },
  });
}

export function useRunTrial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: {
      mutationType: string;
      target: string;
      originalValue: unknown;
      mutatedValue: unknown;
      correctness?: number;
      completeness?: number;
      efficiency?: number;
      confidence?: number;
      latencyMs?: number;
      cost?: number;
    }) => apiClient.post('/evolution/trial', params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['evolution', 'status'] });
      qc.invalidateQueries({ queryKey: ['evolution', 'trials'] });
      qc.invalidateQueries({ queryKey: ['evolution', 'best-practices'] });
    },
  });
}
