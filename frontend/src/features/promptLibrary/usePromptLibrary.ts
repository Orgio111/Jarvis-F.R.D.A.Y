import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface PromptVersion {
  version: number;
  body: string;
  variables: string[];
  created_at: number;
  notes: string;
}

export interface PromptTemplate {
  template_id: string;
  name: string;
  description: string;
  category: string;
  tags: string[];
  active_version: number;
  version_count: number;
  created_at: number;
  updated_at: number;
  usage_count: number;
  metadata: Record<string, unknown>;
  versions?: PromptVersion[];
}

export function usePromptTemplates(category?: string, search?: string) {
  return useQuery({
    queryKey: ['prompts', category, search],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '100' });
      if (category) params.set('category', category);
      if (search) params.set('search', search);
      const res = await apiClient.get<{ templates: PromptTemplate[] }>(`/prompts?${params}`);
      return res.data.templates;
    },
  });
}

export function usePromptTemplate(templateId: string | null) {
  return useQuery({
    queryKey: ['prompts', 'detail', templateId],
    queryFn: async () => {
      const res = await apiClient.get<PromptTemplate>(`/prompts/${templateId}`);
      return res.data;
    },
    enabled: !!templateId,
  });
}

export function useCreatePromptTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; body: string; description?: string; category?: string; tags?: string[] }) => {
      const res = await apiClient.post<PromptTemplate>('/prompts', payload);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  });
}

export function useAddPromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ templateId, body, notes }: { templateId: string; body: string; notes?: string }) => {
      const res = await apiClient.post<PromptTemplate>(`/prompts/${templateId}/versions`, { body, notes: notes ?? '' });
      return res.data;
    },
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ['prompts', 'detail', vars.templateId] });
    },
  });
}

export function useDeletePromptTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (templateId: string) => {
      await apiClient.delete(`/prompts/${templateId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  });
}

export function useRenderPromptTemplate() {
  return useMutation({
    mutationFn: async ({ templateId, variables }: { templateId: string; variables: Record<string, string> }) => {
      const res = await apiClient.post<{ rendered: string }>(`/prompts/${templateId}/render`, { variables });
      return res.data.rendered;
    },
  });
}
