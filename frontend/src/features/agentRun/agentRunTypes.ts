// ─── SSE event types from /orchestrate/run ─────────────────────────────────

export type OrchestratePhase =
  | 'compress'
  | 'file_picker'
  | 'load_files'
  | 'planner'
  | 'parallel'
  | 'sequential'
  | 'review'
  | 'done'
  | 'error';

export interface StatusEvent {
  message: string;
  phase: OrchestratePhase;
  step_ids?: string[];
  step_id?: string;
}

export interface PlanStep {
  id: string;
  description: string;
  agent: string;
  parallel: boolean;
  depends_on: string[];
  context?: Record<string, unknown>;
}

export interface PlanEvent {
  steps: PlanStep[];
  summary: string;
}

export interface CodeEdit {
  path: string;
  content: string;
  mode: 'replace' | 'patch';
  diff?: string;       // unified diff string if mode=patch
}

export interface AgentResultEvent {
  role: string;
  success: boolean;
  content: string;
  data: {
    files?: string[];
    steps?: PlanStep[];
    summary?: string;
    edits?: CodeEdit[];
    issues?: ReviewIssue[];
    approved?: boolean;
    stdout?: string;
    stderr?: string;
    exit_code?: number;
    [key: string]: unknown;
  };
  model_used: string;
  elapsed_ms: number;
  error?: string;
}

export interface ReviewIssue {
  file: string;
  line?: number;
  severity: 'error' | 'warning' | 'info';
  message: string;
}

export interface ReviewEvent {
  approved: boolean;
  issues: ReviewIssue[];
  summary: string;
}

export interface DoneEvent {
  total_steps: number;
  completed: number;
  total_edits: number;
  files_modified: string[];
}

export type OrchestrateEvent =
  | { event: 'status';       data: StatusEvent }
  | { event: 'plan';         data: PlanEvent }
  | { event: 'agent_result'; data: AgentResultEvent }
  | { event: 'review';       data: ReviewEvent }
  | { event: 'step_error';   data: { step_id: string; error: string } }
  | { event: 'done';         data: DoneEvent }
  | { event: 'error';        data: { message: string } };

// ─── UI state ───────────────────────────────────────────────────────────────

export type RunStatus = 'idle' | 'running' | 'done' | 'error';

export interface AgentRunState {
  status: RunStatus;
  phase: OrchestratePhase | null;
  statusMessage: string;
  plan: PlanStep[];
  planSummary: string;
  completedStepIds: Set<string>;
  activeStepIds: Set<string>;
  agentLogs: AgentResultEvent[];
  edits: CodeEdit[];
  review: ReviewEvent | null;
  doneInfo: DoneEvent | null;
  error: string | null;
}
