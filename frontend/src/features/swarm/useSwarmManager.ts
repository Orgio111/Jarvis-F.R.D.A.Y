import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { freshness } from '@/lib/query/freshness';

export interface SwarmSummary {
  swarmId: string;
  role: string;
  agentCount: number;
  state: string;
}

export interface SwarmDetail {
  swarmId: string;
  role: string;
  state: string;
  spec: {
    minAgents: number;
    maxAgents: number;
    initialAgents: number;
    capabilities: string[];
    priority: number;
    autoScale: boolean;
    maxConcurrentTasks: number;
    retryOnFailure: boolean;
  };
  agents: Array<{
    agentId: string;
    role: string;
    state: string;
    confidenceScore: number;
    tasksCompleted: number;
    tasksFailed: number;
    avgLatencyMs: number;
  }>;
  metrics: {
    agentCount: number;
    activeAgents: number;
    idleAgents: number;
    totalTasksCompleted: number;
    totalTasksFailed: number;
    totalTasksRunning: number;
    avgSuccessRate: number;
    avgLatencyMs: number;
    avgConfidence: number;
    utilizationPct: number;
    uptimeSeconds: number;
  } | null;
}

export interface SwarmHealthReport {
  swarmId: string;
  role: string;
  isHealthy: boolean;
  agentCount: number;
  activeAgents: number;
  failedAgents: number;
  utilization: number;
  errorRate: number;
  avgLatencyMs: number;
  issues: string[];
  lastCheck: number;
}

export function useSwarmStatus() {
  return useQuery<{ totalSwarms: number; totalAgents: number; activeAgents: number; swarmRoles: string[] }>({
    queryKey: ['swarm', 'status'],
    queryFn: () => apiClient.get('/swarm/status'),
    staleTime: freshness.slowlyChanging.staleTime,
    gcTime: freshness.slowlyChanging.gcTime,
  });
}

export function useSwarms() {
  return useQuery<{ swarms: SwarmSummary[] }>({
    queryKey: ['swarm', 'list'],
    queryFn: () => apiClient.get('/swarm/swarms'),
    staleTime: freshness.resourceState.staleTime,
    gcTime: freshness.resourceState.gcTime,
  });
}

export function useSwarmDetail(swarmId: string | null) {
  return useQuery<SwarmDetail>({
    queryKey: ['swarm', 'detail', swarmId],
    queryFn: () => apiClient.get(`/swarm/swarms/${swarmId}`),
    enabled: !!swarmId,
    staleTime: freshness.resourceState.staleTime,
    gcTime: freshness.resourceState.gcTime,
  });
}

export function useSwarmHealth() {
  return useQuery<{ health: SwarmHealthReport[] }>({
    queryKey: ['swarm', 'health'],
    queryFn: () => apiClient.get('/swarm/health'),
    staleTime: freshness.live.staleTime,
    gcTime: freshness.live.gcTime,
    refetchInterval: 15_000,
  });
}

export function useCreateSwarm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: { role: string; minAgents: number; maxAgents: number }) =>
      apiClient.post('/swarm/swarms', params),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['swarm', 'list'] });
      qc.invalidateQueries({ queryKey: ['swarm', 'status'] });
    },
  });
}

export function useDeleteSwarm() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (swarmId: string) => apiClient.delete(`/swarm/swarms/${swarmId}`, undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['swarm', 'list'] });
      qc.invalidateQueries({ queryKey: ['swarm', 'status'] });
    },
  });
}

export function useAutoScale() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.post('/swarm/auto-scale'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['swarm', 'health'] });
    },
  });
}

export function useHealSwarms() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => apiClient.post('/swarm/heal'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['swarm', 'health'] });
      qc.invalidateQueries({ queryKey: ['swarm', 'list'] });
    },
  });
}
