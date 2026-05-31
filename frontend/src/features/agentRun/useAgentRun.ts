/**
 * useAgentRun — streams /orchestrate/run SSE events and returns live state.
 *
 * Usage:
 *   const { state, run, abort } = useAgentRun();
 *   await run({ task, fileTree, repoRoot, maxFiles });
 */
import { useCallback, useRef, useState } from 'react';
import { apiUrl } from '@/lib/config/env';
import type {
  AgentRunState,
  AgentResultEvent,
  CodeEdit,
  DoneEvent,
  OrchestratePhase,
  PlanEvent,
  ReviewEvent,
  RunStatus,
  StatusEvent,
} from './agentRunTypes';

const INITIAL_STATE: AgentRunState = {
  status: 'idle',
  phase: null,
  statusMessage: '',
  plan: [],
  planSummary: '',
  completedStepIds: new Set(),
  activeStepIds: new Set(),
  agentLogs: [],
  edits: [],
  review: null,
  doneInfo: null,
  error: null,
};

export interface RunPayload {
  task: string;
  file_tree?: string;
  history?: Array<{ role: string; content: string }>;
  repo_root?: string;
  max_files?: number;
}

export function useAgentRun() {
  const [state, setState] = useState<AgentRunState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const patch = useCallback((updates: Partial<AgentRunState>) => {
    setState((prev) => ({ ...prev, ...updates }));
  }, []);

  const run = useCallback(async (payload: RunPayload) => {
    // Abort any existing run
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setState({
      ...INITIAL_STATE,
      status: 'running',
      statusMessage: 'Initializing...',
    });

    try {
      const response = await fetch(apiUrl('/orchestrate/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
        body: JSON.stringify(payload),
        signal: ctrl.signal,
      });

      if (!response.ok || !response.body) {
        const text = await response.text().catch(() => 'Unknown error');
        throw new Error(`HTTP ${response.status}: ${text}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // ── local mutable accumulators (avoid stale-closure issues) ───────────
      let accEdits: CodeEdit[] = [];
      let accLogs: AgentResultEvent[] = [];
      let completedIds = new Set<string>();
      let activeIds = new Set<string>();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';  // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (!raw || raw === '[DONE]') continue;

          let parsed: { event: string; data: unknown };
          try {
            parsed = JSON.parse(raw);
          } catch {
            continue;
          }

          const { event, data } = parsed as { event: string; data: unknown };

          switch (event) {
            case 'status': {
              const d = data as unknown as StatusEvent;
              const incoming = new Set(d.step_ids ?? (d.step_id ? [d.step_id] : []));
              activeIds = new Set([...activeIds, ...incoming]);
              patch({
                phase: d.phase as OrchestratePhase,
                statusMessage: d.message,
                activeStepIds: new Set(activeIds),
              });
              break;
            }

            case 'plan': {
              const d = data as unknown as PlanEvent;
              patch({
                plan: d.steps,
                planSummary: d.summary,
              });
              break;
            }

            case 'agent_result': {
              const d = data as unknown as AgentResultEvent;
              accLogs = [...accLogs, d];
              const newEdits = d.data?.edits as CodeEdit[] | undefined;
              if (newEdits?.length) {
                accEdits = [...accEdits, ...newEdits];
              }
              patch({ agentLogs: accLogs, edits: accEdits });
              break;
            }

            case 'review': {
              patch({ review: data as unknown as ReviewEvent });
              break;
            }

            case 'step_error': {
              const d = data as unknown as { step_id: string; error: string };
              completedIds = new Set([...completedIds, d.step_id]);
              activeIds.delete(d.step_id);
              patch({
                completedStepIds: new Set(completedIds),
                activeStepIds: new Set(activeIds),
              });
              break;
            }

            case 'done': {
              const d = data as unknown as DoneEvent;
              patch({
                status: 'done' as RunStatus,
                doneInfo: d,
                phase: 'done',
                statusMessage: `Done — ${d.completed}/${d.total_steps} steps, ${d.total_edits} edits`,
                activeStepIds: new Set(),
              });
              break;
            }

            case 'error': {
              patch({
                status: 'error' as RunStatus,
                error: (data as unknown as { message: string }).message,
              });
              break;
            }
          }
        }
      }

      // If stream ended without 'done' event
      setState((prev) =>
        prev.status === 'running'
          ? { ...prev, status: 'done', statusMessage: 'Stream ended.' }
          : prev,
      );
    } catch (err: unknown) {
      if ((err as Error)?.name === 'AbortError') return;
      patch({ status: 'error', error: (err as Error)?.message ?? 'Unknown error' });
    }
  }, [patch]);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    patch({ status: 'idle', statusMessage: 'Aborted.' });
  }, [patch]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  return { state, run, abort, reset };
}
