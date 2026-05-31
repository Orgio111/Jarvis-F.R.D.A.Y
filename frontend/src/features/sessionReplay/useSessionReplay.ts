import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api/client';

export interface ReplaySession {
  session_id: string;
  title: string;
  session_type: 'chat' | 'workflow' | 'agent_run';
  started_at: number;
  ended_at: number | null;
  duration_s: number;
  event_count: number;
  tags: string[];
  model_summary: Record<string, number>;
  metadata: Record<string, unknown>;
}

export interface ReplayEvent {
  event_id: string;
  kind: string;
  timestamp: number;
  data: Record<string, unknown>;
  model_used: string | null;
  duration_ms: number;
}

export interface ReplaySessionDetail extends ReplaySession {
  events: ReplayEvent[];
}

// ── List sessions ─────────────────────────────────────────────────────────────
export function useReplaySessions(sessionType?: string, tag?: string) {
  return useQuery({
    queryKey: ['replay', 'sessions', sessionType, tag],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '50' });
      if (sessionType) params.set('session_type', sessionType);
      if (tag) params.set('tag', tag);
      const res = await apiClient.get<{ sessions: ReplaySession[]; count: number }>(
        `/replay/sessions?${params}`,
      );
      return res.data;
    },
    refetchInterval: 15_000,
  });
}

// ── Get single session ────────────────────────────────────────────────────────
export function useReplaySession(sessionId: string | null) {
  return useQuery({
    queryKey: ['replay', 'session', sessionId],
    queryFn: async () => {
      const res = await apiClient.get<ReplaySessionDetail>(`/replay/sessions/${sessionId}`);
      return res.data;
    },
    enabled: !!sessionId,
  });
}

// ── Create session ────────────────────────────────────────────────────────────
export function useCreateReplaySession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { title: string; session_type: string; tags?: string[] }) => {
      const res = await apiClient.post<ReplaySession>('/replay/sessions', payload);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['replay', 'sessions'] }),
  });
}

// ── Delete session ────────────────────────────────────────────────────────────
export function useDeleteReplaySession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (sessionId: string) => {
      await apiClient.delete(`/replay/sessions/${sessionId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['replay', 'sessions'] }),
  });
}
