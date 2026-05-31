import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Skill, SkillStats, SkillsResponse, SearchResponse } from './types';

const AI_BASE = 'http://localhost:8100';

// ─── Normalizer (camelCase → snake_case + derived fields) ───────────────────

function normalizeSkill(raw: Record<string, any>): Skill {
  const exec = raw.executionCount ?? raw.execution_count ?? 0;
  const succ = raw.successCount ?? raw.success_count ?? 0;
  const latency = raw.latencyMsAvg ?? raw.latency_ms_avg ?? 0;
  const rating = raw.userRating ?? raw.user_rating ?? 0;
  const trust = raw.trustScore ?? raw.trust_score ?? raw.qualityScore ?? raw.quality_score ?? 0;

  return {
    skill_id: raw.skillId ?? raw.skill_id ?? '',
    name: raw.name ?? '',
    description: raw.description ?? '',
    category: raw.category ?? 'general',
    origin: raw.origin ?? 'generated',
    version: raw.version ?? 1,
    enabled: raw.enabled ?? true,
    published: raw.published ?? false,
    publisher: raw.publisher ?? 'system',
    repo_url: raw.repoUrl ?? raw.repo_url,
    hash_sha: raw.hashSha ?? raw.hash_sha,
    trust_score: trust,
    quality_score: raw.qualityScore ?? raw.quality_score ?? trust,
    execution_count: exec,
    success_count: succ,
    latency_ms_avg: latency,
    user_rating: rating,
    rating_count: raw.ratingCount ?? raw.rating_count ?? 0,
    // derived
    usage_count: exec,
    success_rate: exec > 0 ? succ / exec : 0,
    avg_latency_ms: latency,
    avg_rating: rating,
    // extended
    code: raw.sourceCode ?? raw.source_code ?? raw.code,
    icon: raw.icon,
    trigger_patterns: raw.triggerPatterns ?? raw.trigger_patterns ?? raw.triggers ?? [],
    tags: raw.tags ?? [],
    triggers: raw.triggers ?? [],
    dependencies: raw.dependencies ?? [],
    previous_version_id: raw.previousVersionId ?? raw.previous_version_id,
    installed_at: raw.installedAt ?? raw.installed_at,
    created_at: raw.createdAt ?? raw.created_at ?? 0,
    updated_at: raw.updatedAt ?? raw.updated_at ?? 0,
  };
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${AI_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const json = await res.json();
  // Our backend wraps: { ok: true, data: {...} }
  if (json.ok === false) throw new Error(json.error?.message || 'API error');
  return (json.data ?? json) as T;
}

// ─── Simple hook for SkillMarketplacePage ───────────────────────────────────

export function useSkillMarketplace() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [stats, setStats] = useState<SkillStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [skillsRes, statsRes] = await Promise.allSettled([
        fetch(`${AI_BASE}/marketplace/skills`).then((r) => r.json()),
        fetch(`${AI_BASE}/marketplace/stats`).then((r) => r.json()),
      ]);

      if (skillsRes.status === 'fulfilled') {
        const d = skillsRes.value;
        const raw = d.data?.skills ?? d.skills ?? [];
        setSkills(raw.map(normalizeSkill));
      } else {
        setError('Failed to load skills');
      }

      if (statsRes.status === 'fulfilled') {
        const d = statsRes.value;
        const raw = d.data ?? d;
        setStats({
          total_skills: raw.totalSkills ?? raw.total_skills ?? 0,
          enabled_skills: raw.enabledSkills ?? raw.enabled_skills ?? 0,
          total_executions: raw.totalExecutions ?? raw.total_executions ?? 0,
          avg_trust_score: raw.avgTrustScore ?? raw.avg_trust_score ?? 0,
          categories: raw.categories ?? {},
        });
      }
    } catch (e: any) {
      setError(e?.message ?? 'Network error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const generateSkill = async (description: string) => {
    const res = await fetch(`${AI_BASE}/marketplace/install`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: description.slice(0, 60), description }),
    });
    const json = await res.json();
    const raw = json.data ?? json;
    return {
      skill_id: raw.skill?.skillId ?? raw.skill?.skill_id ?? raw.skillId,
      name: raw.skill?.name ?? raw.name ?? description,
      message: raw.message ?? (res.ok ? 'Generated' : 'Failed'),
      detail: json.error?.message,
    };
  };

  const importFromGitHub = async (url: string) => {
    const res = await fetch(`${AI_BASE}/marketplace/github/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    const json = await res.json();
    const raw = json.data ?? json;
    return {
      skill_id: raw.skill?.skillId ?? raw.skill?.skill_id,
      name: raw.skill?.name,
      message: raw.message ?? (res.ok ? 'Imported' : 'Failed'),
      detail: json.error?.message ?? raw.detail,
    };
  };

  const toggleSkill = async (skillId: string, enable: boolean) => {
    const endpoint = enable
      ? `${AI_BASE}/marketplace/install`
      : `${AI_BASE}/marketplace/uninstall/${skillId}`;
    const opts: RequestInit = enable
      ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ skill_id: skillId }) }
      : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' };
    await fetch(endpoint, opts);
  };

  return { skills, stats, loading, error, refresh, generateSkill, importFromGitHub, toggleSkill };
}

// ─── React Query hooks (for advanced use / other components) ─────────────────

export function useMarketplaceSkills(category?: string) {
  const params = category ? `?category=${encodeURIComponent(category)}` : '';
  return useQuery<SkillsResponse>({
    queryKey: ['marketplace', 'skills', category],
    queryFn: async () => {
      const d = await apiFetch<any>(`/marketplace/skills${params}`);
      const raw = d.skills ?? [];
      return { skills: raw.map(normalizeSkill), total: d.total ?? raw.length };
    },
    staleTime: 30_000,
  });
}

export function useTrendingSkills() {
  return useQuery<SkillsResponse>({
    queryKey: ['marketplace', 'trending'],
    queryFn: async () => {
      const d = await apiFetch<any>('/marketplace/trending?limit=20');
      const raw = d.skills ?? [];
      return { skills: raw.map(normalizeSkill), total: d.total ?? raw.length };
    },
    staleTime: 60_000,
  });
}

export function useSearchSkills(q: string, tags: string[], category?: string) {
  const params = new URLSearchParams();
  if (q) params.set('q', q);
  if (tags.length) params.set('tags', tags.join(','));
  if (category) params.set('category', category);
  return useQuery<SearchResponse>({
    queryKey: ['marketplace', 'search', q, tags, category],
    queryFn: async () => {
      const d = await apiFetch<any>(`/marketplace/search?${params}`);
      const raw = d.skills ?? [];
      return { skills: raw.map(normalizeSkill), total: d.total ?? raw.length, query: d.query ?? q, tags: d.tags ?? tags };
    },
    staleTime: 20_000,
    enabled: q.length > 0 || tags.length > 0,
  });
}

export function useSkillDetail(skillId: string | null) {
  return useQuery<{ skill: Skill; version_chain: Skill[] }>({
    queryKey: ['marketplace', 'skill', skillId],
    queryFn: async () => {
      const d = await apiFetch<any>(`/marketplace/skills/${skillId}`);
      return {
        skill: normalizeSkill(d.skill ?? d),
        version_chain: (d.version_chain ?? []).map(normalizeSkill),
      };
    },
    enabled: !!skillId,
    staleTime: 30_000,
  });
}

export function useGitHubStatus() {
  return useQuery<{ git_available: boolean; git_version?: string }>({
    queryKey: ['marketplace', 'github-status'],
    queryFn: () => apiFetch('/marketplace/github/status'),
    staleTime: 300_000,
  });
}

// ─── Mutations ────────────────────────────────────────────────────────────────

export function useInstallSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      apiFetch<{ installed: boolean; skill: Skill; source?: string }>('/marketplace/install', {
        method: 'POST',
        body: JSON.stringify(body),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marketplace'] }),
  });
}

export function useUninstallSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (skillId: string) =>
      apiFetch<{ uninstalled: boolean }>(`/marketplace/uninstall/${skillId}`, { method: 'POST', body: '{}' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marketplace'] }),
  });
}

export function useRateSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ skillId, rating }: { skillId: string; rating: number }) =>
      apiFetch(`/marketplace/rate/${skillId}`, {
        method: 'POST',
        body: JSON.stringify({ rating }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marketplace'] }),
  });
}

export function usePublishSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (skillId: string) =>
      apiFetch(`/marketplace/publish/${skillId}`, { method: 'POST', body: '{}' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marketplace'] }),
  });
}

export function useGitHubImport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ url, category }: { url: string; category?: string }) =>
      apiFetch<{ skill: Skill }>('/marketplace/github/import', {
        method: 'POST',
        body: JSON.stringify({ url, category: category || 'imported' }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marketplace'] }),
  });
}

export function useEvolveSkill() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ skillId, errorContext }: { skillId: string; errorContext?: string }) =>
      apiFetch<{ evolved: boolean; new_skill: Skill }>(`/marketplace/evolve/${skillId}`, {
        method: 'POST',
        body: JSON.stringify({ error_context: errorContext || '' }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marketplace'] }),
  });
}

export function useRunEvolutionCycle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ evolved: number; skipped: number }>('/marketplace/evolve/run', {
        method: 'POST',
        body: '{}',
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['marketplace'] }),
  });
}
