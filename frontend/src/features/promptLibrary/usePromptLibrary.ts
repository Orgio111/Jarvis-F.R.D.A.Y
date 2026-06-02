import { useCallback } from 'react';
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

/** View-model used by PromptLibraryPage */
export interface PromptTemplateView {
  id: string;
  name: string;
  description: string;
  template: string;
  tags: string[];
  variables: string[];
  is_builtin: boolean;
}

function toView(t: PromptTemplate): PromptTemplateView {
  const activeVer = t.versions?.find(v => v.version === t.active_version);
  return {
    id: t.template_id,
    name: t.name,
    description: t.description,
    template: activeVer?.body ?? t.description,
    tags: t.tags,
    variables: activeVer?.variables ?? [],
    is_builtin: t.metadata?.isBuiltin === true || t.category === 'builtin',
  };
}

// ─── Individual hooks (used by usePromptLibrary below) ─────────────────────────

export function usePromptTemplates(category?: string, search?: string) {
  return useQuery({
    queryKey: ['prompts', category, search],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '100' });
      if (category) params.set('category', category);
      if (search) params.set('search', search);
      const res = await apiClient.get<{ templates: PromptTemplate[] }>(`/prompts?${params}`);
      return res.templates;
    },
  });
}

export function usePromptTemplate(templateId: string | null) {
  return useQuery({
    queryKey: ['prompts', 'detail', templateId],
    queryFn: async () => {
      const res = await apiClient.get<PromptTemplate>(`/prompts/${templateId}`);
      return res;
    },
    enabled: !!templateId,
  });
}

export function useCreatePromptTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { name: string; body: string; description?: string; category?: string; tags?: string[] }) => {
      const res = await apiClient.post<PromptTemplate>('/prompts', payload);
      return res;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['prompts'] }),
  });
}

export function useAddPromptVersion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ templateId, body, notes }: { templateId: string; body: string; notes?: string }) => {
      const res = await apiClient.post<PromptTemplate>(`/prompts/${templateId}/versions`, { body, notes: notes ?? '' });
      return res;
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
      return res.rendered;
    },
  });
}

// ─── usePromptLibrary — composite hook for PromptLibraryPage ───────────────────

export function usePromptLibrary() {
  const qc = useQueryClient();

  const { data: rawData, isLoading, error } = useQuery({
    queryKey: ['prompts', 'all'],
    queryFn: async () => {
      const res = await apiClient.get<{ templates: PromptTemplate[] }>('/prompts?limit=100');
      return res.templates;
    },
  });

  const createMut = useCreatePromptTemplate();
  const deleteMut = useDeletePromptTemplate();
  const renderMut = useRenderPromptTemplate();

  const templates = (rawData ?? []).map(toView);

  const filterTemplates = useCallback(
    (searchStr?: string, tag?: string): PromptTemplateView[] => {
      let filtered = templates;
      if (searchStr) {
        const q = searchStr.toLowerCase();
        filtered = filtered.filter(
          t => t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q),
        );
      }
      if (tag) {
        filtered = filtered.filter(t => t.tags.includes(tag));
      }
      return filtered;
    },
    [templates],
  );

  const createTemplate = useCallback(
    async (data: Partial<PromptTemplateView>) => {
      await createMut.mutateAsync({
        name: data.name ?? 'Untitled',
        body: data.template ?? '',
        description: data.description,
        tags: data.tags,
      });
      qc.invalidateQueries({ queryKey: ['prompts'] });
    },
    [createMut, qc],
  );

  const updateTemplate = useCallback(
    async (id: string, data: Partial<PromptTemplateView>) => {
      await apiClient.patch(`/prompts/${id}`, { name: data.name, description: data.description, tags: data.tags });
      qc.invalidateQueries({ queryKey: ['prompts'] });
    },
    [qc],
  );

  const deleteTemplate = useCallback(
    async (id: string) => {
      await deleteMut.mutateAsync(id);
    },
    [deleteMut],
  );

  const applyTemplate = useCallback(
    async (id: string, variables: Record<string, string>): Promise<string | null> => {
      try {
        const result = await renderMut.mutateAsync({ templateId: id, variables });
        return result;
      } catch {
        return null;
      }
    },
    [renderMut],
  );

  return {
    templates,
    loading: isLoading,
    error: error ? (error instanceof Error ? error.message : 'Failed to load templates') : null,
    createTemplate,
    updateTemplate,
    deleteTemplate,
    applyTemplate,
    filterTemplates,
  };
}
