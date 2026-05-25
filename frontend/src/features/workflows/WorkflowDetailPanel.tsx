import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import {
  Workflow,
  Play,
  Plus,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  SkipForward,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  List,
  GitBranch,
  Timer,
  Eye,
} from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { cn } from '@/lib/utils';
import {
  useWorkflowList,
  useWorkflowDetail,
  useCreateWorkflow,
  useRunWorkflow,
  useRunPipeline,
} from './useWorkflowEngine';
import type { WorkflowRunResult } from './useWorkflowEngine';

/* ─────────────────────────────────────────────────────────────────────────────
   Sub-components
   ───────────────────────────────────────────────────────────────────────────── */

/** Status icon mapper */
function StepStatusIcon({ status, size = 14 }: { status: string; size?: number }) {
  switch (status) {
    case 'completed':
      return <CheckCircle2 size={size} className="text-jarvis-green" />;
    case 'running':
      return <Loader2 size={size} className="text-jarvis-cyan animate-spin" />;
    case 'failed':
      return <XCircle size={size} className="text-jarvis-red" />;
    case 'skipped':
      return <SkipForward size={size} className="text-jarvis-text-dim/40" />;
    case 'waiting':
      return <Clock size={size} className="text-jarvis-yellow" />;
    default:
      return <Clock size={size} className="text-jarvis-text-dim/30" />;
  }
}

/** Badge color from status */
function statusBadgeColor(status: string) {
  switch (status) {
    case 'completed':
      return 'green' as const;
    case 'running':
      return 'cyan' as const;
    case 'failed':
      return 'red' as const;
    case 'pending':
      return 'dim' as const;
    default:
      return 'dim' as const;
  }
}

/* ── Section: Create Workflow ──────────────────────────────────────────────── */

function WorkflowCreateSection() {
  const createMut = useCreateWorkflow();
  const pipelineMut = useRunPipeline();
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [stepsJson, setStepsJson] = useState(`[
  {
    "name": "Echo",
    "handler": "echo",
    "params": { "message": "Hello from workflow!" }
  },
  {
    "name": "Log",
    "handler": "log",
    "params": { "message": "Echo completed", "level": "info" }
  }
]`);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = () => {
    setError(null);
    if (!name.trim()) { setError('Workflow name is required.'); return; }
    try {
      const parsed = JSON.parse(stepsJson);
      if (!Array.isArray(parsed)) { setError('Steps must be a JSON array.'); return; }
      createMut.mutate({ name: name.trim(), steps: parsed, description: desc.trim() || undefined });
    } catch {
      setError('Invalid JSON in steps.');
    }
  };

  const handleCreateAndRun = () => {
    setError(null);
    if (!name.trim()) { setError('Workflow name is required.'); return; }
    try {
      const parsed = JSON.parse(stepsJson);
      if (!Array.isArray(parsed)) { setError('Steps must be a JSON array.'); return; }
      pipelineMut.mutate({ name: name.trim(), steps: parsed, context: { description: desc.trim() } });
    } catch {
      setError('Invalid JSON in steps.');
    }
  };

  return (
    <div className="space-y-4">
      <GlassPanel className="p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-wider mb-1 block">
              Workflow Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Workflow"
              className="w-full bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-bright placeholder-jarvis-text-dim/50 focus:outline-none focus:border-jarvis-cyan/60"
            />
          </div>
          <div>
            <label className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-wider mb-1 block">
              Description
            </label>
            <input
              type="text"
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="Optional description"
              className="w-full bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-dim/70 placeholder-jarvis-text-dim/30 focus:outline-none focus:border-jarvis-cyan/60"
            />
          </div>
        </div>

        <div>
          <label className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-wider mb-1 block">
            Step Specs (JSON array)
          </label>
          <textarea
            value={stepsJson}
            onChange={(e) => setStepsJson(e.target.value)}
            rows={8}
            className="w-full bg-jarvis-bg border border-jarvis-border rounded px-3 py-2 text-xs font-mono text-jarvis-text-bright placeholder-jarvis-text-dim/30 focus:outline-none focus:border-jarvis-cyan/60 resize-y font-mono"
            placeholder='[{ "name": "Step 1", "handler": "echo", "params": { "message": "hello" } }]'
          />
          <p className="text-[10px] font-mono text-jarvis-text-dim/40 mt-1">
            Each step needs: <span className="text-jarvis-cyan">name</span>,{' '}
            <span className="text-jarvis-cyan">handler</span>,{' '}
            <span className="text-jarvis-cyan">params</span>. Handlers: echo, delay, log, combine.
          </p>
        </div>

        {error && (
          <p className="text-jarvis-red text-xs font-mono flex items-center gap-1.5">
            <AlertTriangle size={12} /> {error}
          </p>
        )}

        <div className="flex items-center gap-3">
          <CockpitButton
            variant="glow"
            size="sm"
            icon={<Plus size={13} />}
            loading={createMut.isPending}
            onClick={handleCreate}
            disabled={!name.trim()}
          >
            Create Workflow
          </CockpitButton>
          <CockpitButton
            variant="primary"
            size="sm"
            icon={<Play size={13} />}
            loading={pipelineMut.isPending}
            onClick={handleCreateAndRun}
            disabled={!name.trim()}
          >
            Create & Run
          </CockpitButton>
        </div>

        {createMut.data && (
          <m.div
            className="bg-jarvis-bg-2/60 border border-jarvis-green/30 rounded p-3"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <p className="text-jarvis-green text-xs font-mono flex items-center gap-1.5">
              <CheckCircle2 size={12} /> Created:{' '}
              <span className="text-jarvis-text-bright">{createMut.data.name}</span>
              <span className="text-jarvis-text-dim/50 ml-1">({createMut.data.id})</span>
            </p>
          </m.div>
        )}

        {pipelineMut.data && <RunResultCard result={pipelineMut.data} />}
      </GlassPanel>
    </div>
  );
}

/* ── Section: Execution History ────────────────────────────────────────────── */

function WorkflowHistorySection() {
  const { data: workflows = [], isLoading } = useWorkflowList();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const runMut = useRunWorkflow();

  const executions = workflows.filter(
    (w) => w.status === 'completed' || w.status === 'failed' || w.status === 'cancelled',
  );

  if (isLoading) {
    return <div className="text-jarvis-text-dim text-xs font-mono">Loading history…</div>;
  }

  if (executions.length === 0) {
    return (
      <GlassPanel className="p-8 text-center">
        <Clock size={36} className="mx-auto text-jarvis-text-dim/20 mb-3" />
        <p className="text-jarvis-text-dim text-sm font-mono">No execution history yet.</p>
        <p className="text-jarvis-text-dim/50 text-xs font-mono mt-2">
          Run a workflow to see results here.
        </p>
      </GlassPanel>
    );
  }

  return (
    <div className="space-y-3">
      <AnimatePresence mode="popLayout">
        {executions.map((wf, i) => (
          <m.div
            key={wf.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: i * 0.03 }}
          >
            <GlassPanel className="p-4" hover onClick={() => setExpandedId(expandedId === wf.id ? null : wf.id)}>
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-jarvis-text-bright text-sm font-mono truncate">{wf.name}</p>
                    <NeonBadge label={wf.status} color={statusBadgeColor(wf.status)} size="sm" />
                  </div>
                  <p className="text-jarvis-text-dim/50 text-[10px] font-mono mt-0.5">
                    {wf.stepCount} step{wf.stepCount !== 1 ? 's' : ''}
                    {wf.createdAt && ` · ${new Date(wf.createdAt * 1000).toLocaleString()}`}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  <CockpitButton
                    variant="ghost"
                    size="sm"
                    icon={<Play size={11} />}
                    onClick={(e: React.MouseEvent) => {
                      e.stopPropagation();
                      runMut.mutate({ workflowId: wf.id });
                    }}
                    loading={runMut.isPending && runMut.variables?.workflowId === wf.id}
                  >
                    Re-run
                  </CockpitButton>
                  <span className="text-jarvis-text-dim/50">
                    {expandedId === wf.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </span>
                </div>
              </div>

              {expandedId === wf.id && <WorkflowDetailView workflowId={wf.id} />}
            </GlassPanel>
          </m.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

/* ── Section: Active Workflows Monitor ─────────────────────────────────────── */

function WorkflowMonitorSection() {
  const { data: workflows = [], isLoading, refetch } = useWorkflowList();
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const active = workflows.filter(
    (w) => w.status === 'running' || w.status === 'pending',
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-jarvis-text-dim text-[10px] font-mono uppercase tracking-wider">
          <Eye size={11} className="inline mr-1" />
          Active Workflows
          {active.length > 0 && (
            <span className="ml-2 text-jarvis-cyan">({active.length})</span>
          )}
        </p>
        <CockpitButton variant="ghost" size="sm" icon={<Loader2 size={11} />} onClick={() => refetch()}>
          Refresh
        </CockpitButton>
      </div>

      {isLoading ? (
        <div className="text-jarvis-text-dim text-xs font-mono">Loading monitor…</div>
      ) : active.length === 0 ? (
        <GlassPanel className="p-6 text-center">
          <Eye size={28} className="mx-auto text-jarvis-text-dim/20 mb-2" />
          <p className="text-jarvis-text-dim text-xs font-mono">No active workflows.</p>
          <p className="text-jarvis-text-dim/40 text-[10px] font-mono mt-1">
            Create and run a workflow to see it here.
          </p>
        </GlassPanel>
      ) : (
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {active.map((wf, i) => (
              <m.div
                key={wf.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2, delay: i * 0.04 }}
              >
                <GlassPanel className="p-4" hover onClick={() => setExpandedId(expandedId === wf.id ? null : wf.id)}>
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <m.span
                          className="w-2 h-2 rounded-full bg-jarvis-cyan"
                          animate={{ opacity: [1, 0.3, 1], scale: [1, 1.3, 1] }}
                          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                        />
                        <p className="text-jarvis-text-bright text-sm font-mono truncate">{wf.name}</p>
                        <NeonBadge label={wf.status} color="cyan" size="sm" pulse />
                      </div>
                      <p className="text-jarvis-text-dim/50 text-[10px] font-mono mt-0.5">
                        {wf.stepCount} step{wf.stepCount !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <span className="text-jarvis-text-dim/50 shrink-0 ml-2">
                      {expandedId === wf.id ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                    </span>
                  </div>

                  {expandedId === wf.id && <WorkflowDetailView workflowId={wf.id} />}
                </GlassPanel>
              </m.div>
            ))}
          </AnimatePresence>

          {workflows.filter((w) => w.status === 'completed' || w.status === 'failed').length > 0 && (
            <div className="pt-2">
              <p className="text-jarvis-text-dim/40 text-[10px] font-mono">
                {workflows.filter((w) => w.status === 'completed' || w.status === 'failed').length} completed/failed
                workflows — see the History tab for details.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Shared: Workflow Detail View (expanded card) ─────────────────────────── */

function WorkflowDetailView({ workflowId }: { workflowId: string }) {
  const { data: detail, isLoading } = useWorkflowDetail(workflowId);
  const runMut = useRunWorkflow();

  if (isLoading) {
    return (
      <m.div
        className="mt-3 pt-3 border-t border-jarvis-border/20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <p className="text-jarvis-text-dim text-xs font-mono">Loading details…</p>
      </m.div>
    );
  }

  if (!detail) {
    return (
      <m.div
        className="mt-3 pt-3 border-t border-jarvis-border/20"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        <p className="text-jarvis-text-dim text-xs font-mono">Workflow not found.</p>
      </m.div>
    );
  }

  return (
    <m.div
      className="mt-3 pt-3 border-t border-jarvis-border/20 space-y-3"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
    >
      {/* Meta */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
        <div className="p-2 rounded bg-jarvis-bg-2/40 border border-jarvis-border/10">
          <p className="text-jarvis-text-dim/50 text-[10px]">Version</p>
          <p className="text-jarvis-text-bright">{detail.version}</p>
        </div>
        <div className="p-2 rounded bg-jarvis-bg-2/40 border border-jarvis-border/10">
          <p className="text-jarvis-text-dim/50 text-[10px]">Steps</p>
          <p className="text-jarvis-text-bright">{detail.steps.length}</p>
        </div>
        <div className="p-2 rounded bg-jarvis-bg-2/40 border border-jarvis-border/10">
          <p className="text-jarvis-text-dim/50 text-[10px]">Status</p>
          <p className="capitalize">{detail.status}</p>
        </div>
        <div className="p-2 rounded bg-jarvis-bg-2/40 border border-jarvis-border/10">
          <p className="text-jarvis-text-dim/50 text-[10px]">Tags</p>
          <p className="text-jarvis-text-bright">{detail.tags?.join(', ') || '—'}</p>
        </div>
      </div>

      {detail.description && (
        <p className="text-jarvis-text-dim/60 text-xs font-mono italic">{detail.description}</p>
      )}

      {/* Steps list */}
      <div>
        <p className="text-jarvis-text-dim/60 text-[10px] font-mono uppercase tracking-wider mb-2 flex items-center gap-1">
          <GitBranch size={10} /> Steps
        </p>
        <div className="space-y-1 max-h-48 overflow-y-auto pr-1" style={{ scrollbarWidth: 'thin' }}>
          {detail.steps.map((step, i) => (
            <div
              key={step.id}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded bg-jarvis-bg-3/20 hover:bg-jarvis-bg-3/40 transition-colors text-xs font-mono"
            >
              <StepStatusIcon status={step.status} />
              <span className="text-jarvis-text-dim/50 w-5 shrink-0">#{i}</span>
              <span className="text-jarvis-text-bright flex-1 truncate">{step.name}</span>
              <NeonBadge label={step.type} color="dim" size="sm" />
              {step.handler && (
                <span className="text-jarvis-cyan/60 text-[10px] hidden sm:inline">{step.handler}</span>
              )}
              {step.error && (
                <span className="text-jarvis-red text-[10px] truncate max-w-[120px]" title={step.error}>
                  {step.error}
                </span>
              )}
              {step.dependsOn.length > 0 && (
                <span className="text-jarvis-text-dim/30 text-[10px]">← {step.dependsOn.length}</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Action */}
      {(detail.status === 'pending' || detail.status === 'failed' || detail.status === 'completed') && (
        <div className="pt-1">
          <CockpitButton
            variant="glow"
            size="sm"
            icon={<Play size={11} />}
            onClick={() => runMut.mutate({ workflowId: detail.id })}
            loading={runMut.isPending && runMut.variables?.workflowId === detail.id}
          >
            {detail.status === 'completed' ? 'Re-run' : detail.status === 'failed' ? 'Retry' : 'Run'}
          </CockpitButton>
        </div>
      )}
    </m.div>
  );
}

/* ── Shared: Run Result Card ───────────────────────────────────────────────── */

function RunResultCard({ result }: { result: WorkflowRunResult }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <m.div
      className={cn(
        'border rounded-lg overflow-hidden',
        result.success ? 'border-jarvis-green/30' : 'border-jarvis-red/30',
      )}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div
        className={cn(
          'flex items-center justify-between px-4 py-3 cursor-pointer',
          result.success ? 'bg-jarvis-green/5' : 'bg-jarvis-red/5',
        )}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          {result.success ? (
            <CheckCircle2 size={16} className="text-jarvis-green" />
          ) : (
            <XCircle size={16} className="text-jarvis-red" />
          )}
          <div>
            <p className="text-jarvis-text-bright text-xs font-mono font-semibold">
              {result.success ? 'Pipeline completed' : 'Pipeline failed'}
            </p>
            <p className="text-jarvis-text-dim/50 text-[10px] font-mono mt-0.5 flex items-center gap-2">
              <Timer size={10} /> {result.durationMs.toFixed(0)}ms
              <span className="text-jarvis-text-dim/30">·</span>
              <span className="text-jarvis-green">{result.completedSteps}/{result.totalSteps} steps</span>
              {result.failedSteps > 0 && (
                <span className="text-jarvis-red">{result.failedSteps} failed</span>
              )}
            </p>
          </div>
        </div>
        <span className="text-jarvis-text-dim/50">{expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</span>
      </div>

      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {result.error && (
            <div className="bg-jarvis-red/5 border border-jarvis-red/20 rounded p-2 text-jarvis-red text-[11px] font-mono">
              {result.error}
            </div>
          )}
          <div className="text-xs font-mono">
            <p className="text-jarvis-text-dim/60 text-[10px] mb-1">Step Results</p>
            <div className="space-y-1 max-h-32 overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
              {Object.entries(result.steps).map(([stepId, stepResult]) => (
                <div key={stepId} className="flex items-center gap-2 px-2 py-1 rounded bg-jarvis-bg-3/20">
                  <StepStatusIcon status={stepResult.status} size={10} />
                  <span className="text-jarvis-text-dim/60 text-[10px] w-20 truncate">{stepId}</span>
                  <span className="text-jarvis-text-dim/40 text-[10px]">{stepResult.status}</span>
                  {stepResult.error && (
                    <span className="text-jarvis-red text-[10px] truncate flex-1">{stepResult.error}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </m.div>
  );
}

/* ── Pipeline Quick Runner (inline utility) ───────────────────────────────── */

function PipelineQuickRunner() {
  const [handler, setHandler] = useState('echo');
  const [paramsJson, setParamsJson] = useState('{ "message": "Hello JARVIS" }');
  const pipelineMut = useRunPipeline();
  const [error, setError] = useState<string | null>(null);

  const handleRun = () => {
    setError(null);
    try {
      const params = JSON.parse(paramsJson);
      pipelineMut.mutate({
        name: `Quick ${handler}`,
        steps: [{ name: handler, handler, params }],
      });
    } catch {
      setError('Invalid JSON params');
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2">
        <select
          value={handler}
          onChange={(e) => setHandler(e.target.value)}
          className="bg-jarvis-bg border border-jarvis-border rounded px-2 py-1.5 text-xs font-mono text-jarvis-text-bright focus:outline-none focus:border-jarvis-cyan/60 shrink-0"
        >
          <option value="echo">echo</option>
          <option value="delay">delay</option>
          <option value="log">log</option>
          <option value="combine">combine</option>
        </select>
        <input
          type="text"
          value={paramsJson}
          onChange={(e) => setParamsJson(e.target.value)}
          placeholder='{ "key": "value" }'
          className="flex-1 bg-jarvis-bg border border-jarvis-border rounded px-2 py-1.5 text-xs font-mono text-jarvis-text-dim/70 placeholder-jarvis-text-dim/30 focus:outline-none focus:border-jarvis-cyan/60"
        />
        <CockpitButton
          variant="glow"
          size="sm"
          icon={<Play size={11} />}
          loading={pipelineMut.isPending}
          onClick={handleRun}
          disabled={!handler}
        >
          Run
        </CockpitButton>
      </div>

      {error && <p className="text-jarvis-red text-[10px] font-mono">{error}</p>}

      {pipelineMut.data && <RunResultCard result={pipelineMut.data} />}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────────────────────
   Main Panel Component
   ───────────────────────────────────────────────────────────────────────────── */

export function WorkflowDetailPanel() {
  const [activeTab, setActiveTab] = useState<'create' | 'monitor' | 'history'>('create');

  const tabs = [
    { id: 'create' as const, label: 'Create', icon: Plus },
    { id: 'monitor' as const, label: 'Monitor', icon: Eye },
    { id: 'history' as const, label: 'History', icon: List },
  ];

  return (
    <div className="p-6 overflow-auto h-full space-y-6">
      <SectionHeader
        title={
          <span className="inline-flex items-center gap-2">
            <Workflow size={16} className="text-jarvis-cyan" />
            Workflow Engine
          </span>
        }
        subtitle="Create, monitor, and review workflow executions"
      />

      {/* Tab bar */}
      <div className="flex items-center gap-1 border-b border-jarvis-border/20 pb-px">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-1.5 px-4 py-2 text-xs font-mono transition-all duration-200 border-b-2 -mb-px',
                isActive
                  ? 'text-jarvis-cyan border-jarvis-cyan'
                  : 'text-jarvis-text-dim/50 border-transparent hover:text-jarvis-text-dim hover:border-jarvis-border/30',
              )}
            >
              <Icon size={13} />
              {tab.label}
            </button>
          );
        })}

        <div className="flex-1" />

        {/* Quick runner (always visible) */}
        <PipelineQuickRunner />
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        <m.div
          key={activeTab}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'create' && <WorkflowCreateSection />}
          {activeTab === 'monitor' && <WorkflowMonitorSection />}
          {activeTab === 'history' && <WorkflowHistorySection />}
        </m.div>
      </AnimatePresence>
    </div>
  );
}
