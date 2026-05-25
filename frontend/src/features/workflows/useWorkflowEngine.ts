import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';
import { useBootstrapStore } from '@/features/bootstrap/bootstrapStore';
import { freshness } from '@/lib/query/freshness';

interface WorkflowSummary {
  id: string;
  name: string;
  status: string;
  stepCount: number;
  createdAt?: number;
  tags?: string[];
}

interface WorkflowDetail {
  id: string;
  name: string;
  description: string;
  version: string;
  status: string;
  steps: Array<{
    id: string;
    name: string;
    type: string;
    status: string;
    dependsOn: string[];
    handler: string | null;
    error: string | null;
  }>;
  context: Record<string, unknown>;
  createdAt?: number;
  tags?: string[];
}

export interface WorkflowRunResult {
  success: boolean;
  workflowId: string;
  status: string;
  totalSteps: number;
  completedSteps: number;
  failedSteps: number;
  durationMs: number;
  steps: Record<string, { status: string; error?: string }>;
  context: Record<string, unknown>;
  error?: string;
}

export function useWorkflowList() {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  return useQuery<WorkflowSummary[]>({
    queryKey: ['workflows', 'engine', 'list'],
    queryFn: () => apiClient.get<WorkflowSummary[]>('/workflows/engine/list'),
    enabled: bootstrapReady,
    ...freshness.slowlyChanging,
  });
}

export function useWorkflowDetail(workflowId: string | null) {
  const bootstrapReady = useBootstrapStore((s) => s.status === 'ready');

  return useQuery<WorkflowDetail>({
    queryKey: ['workflows', 'engine', workflowId],
    queryFn: () => apiClient.get<WorkflowDetail>(`/workflows/engine/${workflowId}`),
    enabled: bootstrapReady && workflowId !== null,
    ...freshness.resourceState,
  });
}

export function useCreateWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { name: string; steps: Array<Record<string, unknown>>; description?: string }) =>
      apiClient.post<WorkflowSummary>('/workflows/engine/create', params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'engine', 'list'] });
    },
  });
}

export function useRunWorkflow() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { workflowId: string; context?: Record<string, unknown> }) =>
      apiClient.post<WorkflowRunResult>('/workflows/engine/run', params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'engine'] });
    },
  });
}

export function useRunPipeline() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { name?: string; steps: Array<Record<string, unknown>>; context?: Record<string, unknown> }) =>
      apiClient.post<WorkflowRunResult>('/workflows/engine/pipeline', params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workflows', 'engine'] });
    },
  });
}
