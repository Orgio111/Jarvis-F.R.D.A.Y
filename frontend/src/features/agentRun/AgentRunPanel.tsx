/**
 * AgentRunPanel — Freebuff/Codebuff-style multi-agent orchestration UI.
 *
 * Features:
 *  - Streaming SSE phases with live status bar
 *  - Animated plan steps (parallel / sequential indicators)
 *  - Live agent logs with model badges
 *  - Diff-based code output (DiffBlock)
 *  - Review results with issue severity badges
 *  - Abort button
 */
import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import {
  Bot, Play, Square, RefreshCw, ChevronDown, ChevronRight,
  GitBranch, Zap, CheckCircle2, XCircle, AlertTriangle,
  Clock, FileCode2, GitMerge, Eye, Layers,
} from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { DiffBlock } from './DiffBlock';
import { useAgentRun } from './useAgentRun';
import type { AgentResultEvent, PlanStep, ReviewIssue } from './agentRunTypes';

// ─── Phase colour map ─────────────────────────────────────────────────────────
const PHASE_COLOR: Record<string, string> = {
  compress:    'text-jarvis-text-dim',
  file_picker: 'text-yellow-400',
  load_files:  'text-yellow-300',
  planner:     'text-jarvis-blue',
  parallel:    'text-jarvis-purple',
  sequential:  'text-jarvis-cyan',
  review:      'text-orange-400',
  done:        'text-green-400',
  error:       'text-jarvis-red',
};

const AGENT_COLOR: Record<string, string> = {
  editor:      'text-jarvis-cyan',
  terminal:    'text-jarvis-green',
  reviewer:    'text-orange-400',
  file_picker: 'text-yellow-400',
  planner:     'text-jarvis-blue',
};

const SEVERITY_STYLES: Record<string, string> = {
  error:   'border-jarvis-red/40 bg-jarvis-red/5 text-jarvis-red',
  warning: 'border-yellow-500/40 bg-yellow-500/5 text-yellow-300',
  info:    'border-jarvis-blue/40 bg-jarvis-blue/5 text-jarvis-text-dim',
};

// ─── Main panel ───────────────────────────────────────────────────────────────

export function AgentRunPanel() {
  const { state, run, abort, reset } = useAgentRun();

  const [task, setTask]         = useState('');
  const [repoRoot, setRepoRoot] = useState('');
  const [fileTree, setFileTree] = useState('');
  const [maxFiles, setMaxFiles] = useState(10);
  const [showConfig, setShowConfig] = useState(false);

  const handleRun = () => {
    if (!task.trim()) return;
    run({
      task: task.trim(),
      repo_root: repoRoot.trim() || undefined,
      file_tree: fileTree.trim() || undefined,
      max_files: maxFiles,
    });
  };

  const isRunning = state.status === 'running';
  const isDone    = state.status === 'done';
  const isError   = state.status === 'error';

  return (
    <div className="flex flex-col h-full gap-4 p-5 overflow-y-auto scrollbar-thin">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-xl bg-jarvis-purple/10 border border-jarvis-purple/30 flex items-center justify-center">
          <GitBranch size={16} className="text-jarvis-purple" />
        </div>
        <div>
          <h2 className="text-jarvis-text-bright text-sm font-mono font-semibold tracking-wide">
            AGENT ORCHESTRATOR
          </h2>
          <p className="text-jarvis-text-dim text-[10px] font-mono">
            Freebuff-style multi-agent pipeline · free OpenRouter models
          </p>
        </div>

        {/* Status pill */}
        {state.status !== 'idle' && (
          <m.span
            key={state.status}
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className={[
              'ml-auto px-2.5 py-1 rounded-full text-[10px] font-mono border',
              isRunning ? 'bg-jarvis-cyan/10 border-jarvis-cyan/30 text-jarvis-cyan'
              : isDone  ? 'bg-green-400/10 border-green-400/30 text-green-400'
              : isError ? 'bg-jarvis-red/10 border-jarvis-red/30 text-jarvis-red'
              : '',
            ].join(' ')}
          >
            {isRunning ? '● RUNNING' : isDone ? '✓ DONE' : '✗ ERROR'}
          </m.span>
        )}
      </div>

      {/* ── Task input ─────────────────────────────────────────────────────── */}
      <GlassPanel className="p-4 shrink-0">
        <label className="text-jarvis-text-dim text-[10px] font-mono tracking-widest mb-2 block">
          TASK
        </label>
        <textarea
          className="w-full bg-transparent text-jarvis-text-bright text-sm font-mono resize-none outline-none placeholder-jarvis-text-dim/40 leading-relaxed"
          rows={3}
          placeholder="e.g. Add type hints to all Python files in src/"
          value={task}
          onChange={(e) => setTask(e.target.value)}
          disabled={isRunning}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleRun();
          }}
        />

        {/* Config toggle */}
        <button
          className="mt-2 text-[10px] font-mono text-jarvis-text-dim hover:text-jarvis-cyan flex items-center gap-1 transition-colors"
          onClick={() => setShowConfig((v) => !v)}
        >
          {showConfig ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          advanced config
        </button>

        <AnimatePresence>
          {showConfig && (
            <m.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="overflow-hidden"
            >
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div>
                  <label className="text-[10px] font-mono text-jarvis-text-dim mb-1 block">REPO ROOT PATH</label>
                  <input
                    className="w-full bg-jarvis-bg/60 border border-jarvis-border/40 rounded-lg px-3 py-1.5 text-xs font-mono text-jarvis-text-bright outline-none focus:border-jarvis-cyan/40"
                    placeholder="/workspace/myproject"
                    value={repoRoot}
                    onChange={(e) => setRepoRoot(e.target.value)}
                    disabled={isRunning}
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-jarvis-text-dim mb-1 block">MAX FILES</label>
                  <input
                    type="number"
                    className="w-full bg-jarvis-bg/60 border border-jarvis-border/40 rounded-lg px-3 py-1.5 text-xs font-mono text-jarvis-text-bright outline-none focus:border-jarvis-cyan/40"
                    value={maxFiles}
                    min={1}
                    max={50}
                    onChange={(e) => setMaxFiles(parseInt(e.target.value) || 10)}
                    disabled={isRunning}
                  />
                </div>
                <div className="col-span-2">
                  <label className="text-[10px] font-mono text-jarvis-text-dim mb-1 block">FILE TREE (optional — newline separated paths)</label>
                  <textarea
                    className="w-full bg-jarvis-bg/60 border border-jarvis-border/40 rounded-lg px-3 py-1.5 text-xs font-mono text-jarvis-text-bright outline-none focus:border-jarvis-cyan/40 resize-none"
                    rows={3}
                    placeholder={"src/main.py\nsrc/utils.py\ntests/test_main.py"}
                    value={fileTree}
                    onChange={(e) => setFileTree(e.target.value)}
                    disabled={isRunning}
                  />
                </div>
              </div>
            </m.div>
          )}
        </AnimatePresence>

        {/* Action buttons */}
        <div className="flex gap-2 mt-3">
          {!isRunning ? (
            <button
              onClick={handleRun}
              disabled={!task.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-jarvis-purple/20 border border-jarvis-purple/40 text-jarvis-purple text-xs font-mono font-semibold hover:bg-jarvis-purple/30 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Play size={12} />
              {isDone || isError ? 'Re-run' : 'Run Pipeline'}
              <span className="text-[9px] opacity-50 font-normal ml-1">⌘↵</span>
            </button>
          ) : (
            <button
              onClick={abort}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-jarvis-red/10 border border-jarvis-red/30 text-jarvis-red text-xs font-mono hover:bg-jarvis-red/20 transition-all duration-200"
            >
              <Square size={12} />
              Abort
            </button>
          )}
          {(isDone || isError) && (
            <button
              onClick={reset}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border border-jarvis-border/40 text-jarvis-text-dim text-xs font-mono hover:text-jarvis-cyan hover:border-jarvis-cyan/30 transition-all duration-200"
            >
              <RefreshCw size={12} />
              Reset
            </button>
          )}
        </div>
      </GlassPanel>

      {/* ── Live status bar ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {state.statusMessage && (
          <m.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="flex items-center gap-3 px-4 py-2.5 rounded-xl border border-jarvis-border/30 bg-jarvis-bg-2/40 shrink-0"
          >
            {isRunning && (
              <m.span
                className="w-1.5 h-1.5 rounded-full bg-jarvis-cyan shrink-0"
                animate={{ opacity: [1, 0.3, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
            )}
            <span className={`text-xs font-mono ${PHASE_COLOR[state.phase ?? ''] ?? 'text-jarvis-text-dim'}`}>
              [{state.phase?.toUpperCase() ?? '...'}]
            </span>
            <span className="text-jarvis-text-bright text-xs font-mono">{state.statusMessage}</span>
          </m.div>
        )}
      </AnimatePresence>

      {/* ── Error banner ───────────────────────────────────────────────────── */}
      <AnimatePresence>
        {isError && state.error && (
          <m.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-3 px-4 py-3 rounded-xl border border-jarvis-red/30 bg-jarvis-red/5 shrink-0"
          >
            <XCircle size={14} className="text-jarvis-red mt-0.5 shrink-0" />
            <span className="text-jarvis-red text-xs font-mono">{state.error}</span>
          </m.div>
        )}
      </AnimatePresence>

      {/* ── Plan steps ────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {state.plan.length > 0 && (
          <m.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            className="shrink-0"
          >
            <SectionHeader icon={<Layers size={13} />} title="PLAN" badge={`${state.plan.length} steps`} />
            {state.planSummary && (
              <p className="text-jarvis-text-dim text-[10px] font-mono mb-2 mt-1 px-1">
                {state.planSummary}
              </p>
            )}
            <div className="space-y-1.5">
              {state.plan.map((step) => (
                <PlanStepRow
                  key={step.id}
                  step={step}
                  isActive={state.activeStepIds.has(step.id)}
                  isDone={state.completedStepIds.has(step.id)}
                />
              ))}
            </div>
          </m.div>
        )}
      </AnimatePresence>

      {/* ── Agent log stream ──────────────────────────────────────────────── */}
      <AnimatePresence>
        {state.agentLogs.length > 0 && (
          <m.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <SectionHeader icon={<Bot size={13} />} title="AGENT LOGS" badge={`${state.agentLogs.length}`} />
            <div className="space-y-1.5 mt-2">
              {state.agentLogs.map((log, i) => (
                <AgentLogRow key={i} log={log} index={i} />
              ))}
            </div>
          </m.div>
        )}
      </AnimatePresence>

      {/* ── Diff edits ────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {state.edits.length > 0 && (
          <m.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <SectionHeader
              icon={<FileCode2 size={13} />}
              title="CODE EDITS"
              badge={`${state.edits.length} file${state.edits.length > 1 ? 's' : ''}`}
              color="text-jarvis-cyan"
            />
            <div className="space-y-2 mt-2">
              {state.edits.map((edit, i) => (
                <DiffBlock key={`${edit.path}-${i}`} edit={edit} index={i} />
              ))}
            </div>
          </m.div>
        )}
      </AnimatePresence>

      {/* ── Review results ────────────────────────────────────────────────── */}
      <AnimatePresence>
        {state.review && (
          <m.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <SectionHeader
              icon={<Eye size={13} />}
              title="REVIEW"
              badge={state.review.approved ? '✓ APPROVED' : '⚠ ISSUES FOUND'}
              color={state.review.approved ? 'text-green-400' : 'text-orange-400'}
            />
            {state.review.summary && (
              <p className="text-jarvis-text-dim text-[10px] font-mono mb-2 px-1">
                {state.review.summary}
              </p>
            )}
            {state.review.issues.length > 0 && (
              <div className="space-y-1.5 mt-2">
                {state.review.issues.map((issue, i) => (
                  <ReviewIssueRow key={i} issue={issue} />
                ))}
              </div>
            )}
          </m.div>
        )}
      </AnimatePresence>

      {/* ── Done summary ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {isDone && state.doneInfo && (
          <m.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <GlassPanel className="p-4" glow>
              <div className="flex items-center gap-3 mb-3">
                <CheckCircle2 size={18} className="text-green-400" />
                <span className="text-green-400 text-sm font-mono font-semibold">Pipeline Complete</span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <StatBox label="STEPS" value={`${state.doneInfo.completed}/${state.doneInfo.total_steps}`} />
                <StatBox label="EDITS" value={String(state.doneInfo.total_edits)} />
                <StatBox label="FILES" value={String(state.doneInfo.files_modified.length)} />
              </div>
              {state.doneInfo.files_modified.length > 0 && (
                <div className="mt-3 pt-3 border-t border-jarvis-border/20">
                  <p className="text-jarvis-text-dim text-[10px] font-mono mb-1.5">MODIFIED FILES</p>
                  <div className="flex flex-wrap gap-1.5">
                    {state.doneInfo.files_modified.map((f) => (
                      <span key={f} className="text-[10px] font-mono text-jarvis-cyan bg-jarvis-cyan/5 border border-jarvis-cyan/20 px-2 py-0.5 rounded">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </GlassPanel>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function SectionHeader({
  icon, title, badge, color = 'text-jarvis-text-dim',
}: {
  icon: React.ReactNode;
  title: string;
  badge?: string;
  color?: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-2">
      <span className={color}>{icon}</span>
      <span className={`text-[10px] font-mono font-semibold tracking-widest ${color}`}>{title}</span>
      {badge && (
        <span className="text-[9px] font-mono text-jarvis-text-dim bg-jarvis-bg-2/60 border border-jarvis-border/30 px-1.5 py-0.5 rounded">
          {badge}
        </span>
      )}
      <div className="flex-1 h-px bg-jarvis-border/20" />
    </div>
  );
}

function PlanStepRow({
  step, isActive, isDone,
}: {
  step: PlanStep;
  isActive: boolean;
  isDone: boolean;
}) {
  return (
    <m.div
      className={[
        'flex items-center gap-3 px-3 py-2 rounded-lg border text-xs font-mono transition-all duration-300',
        isActive
          ? 'border-jarvis-cyan/40 bg-jarvis-cyan/5 text-jarvis-text-bright'
          : isDone
          ? 'border-green-500/20 bg-green-500/5 text-jarvis-text-dim'
          : 'border-jarvis-border/20 bg-transparent text-jarvis-text-dim/60',
      ].join(' ')}
      animate={isActive ? { boxShadow: ['0 0 0px rgba(0,212,255,0)', '0 0 8px rgba(0,212,255,0.15)', '0 0 0px rgba(0,212,255,0)'] } : {}}
      transition={{ duration: 1.5, repeat: Infinity }}
    >
      {/* Status icon */}
      <span className="shrink-0">
        {isDone
          ? <CheckCircle2 size={12} className="text-green-400" />
          : isActive
          ? <m.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}>
              <RefreshCw size={12} className="text-jarvis-cyan" />
            </m.span>
          : <Clock size={12} className="text-jarvis-text-dim/40" />
        }
      </span>

      {/* Step ID */}
      <span className="text-[9px] text-jarvis-text-dim/50 shrink-0 w-10">{step.id}</span>

      {/* Description */}
      <span className="flex-1 truncate">{step.description}</span>

      {/* Agent badge */}
      <span className={`shrink-0 text-[9px] ${AGENT_COLOR[step.agent] ?? 'text-jarvis-text-dim'}`}>
        {step.agent}
      </span>

      {/* Parallel badge */}
      {step.parallel && (
        <span className="shrink-0">
          <GitMerge size={10} className="text-jarvis-purple" title="parallel" />
        </span>
      )}
      {step.depends_on.length > 0 && (
        <span className="text-[9px] text-jarvis-text-dim/40 shrink-0">
          deps: {step.depends_on.join(',')}
        </span>
      )}
    </m.div>
  );
}

function AgentLogRow({ log, index }: { log: AgentResultEvent; index: number }) {
  const [open, setOpen] = useState(false);

  return (
    <m.div
      className="border border-jarvis-border/30 rounded-lg overflow-hidden"
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.2, delay: index * 0.03 }}
    >
      <button
        className="w-full flex items-center gap-3 px-3 py-2 text-xs font-mono hover:bg-jarvis-bg-3/30 transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}

        {/* Role */}
        <span className={`${AGENT_COLOR[log.role] ?? 'text-jarvis-text-dim'} shrink-0 w-20`}>
          {log.role}
        </span>

        {/* Status */}
        <span className="shrink-0">
          {log.success
            ? <CheckCircle2 size={11} className="text-green-400" />
            : <XCircle size={11} className="text-jarvis-red" />
          }
        </span>

        {/* Summary content */}
        <span className="text-jarvis-text-dim flex-1 truncate text-left">
          {log.content.slice(0, 100)}
        </span>

        {/* Model */}
        {log.model_used && (
          <span className="text-[9px] text-jarvis-text-dim/50 shrink-0 truncate max-w-[120px]">
            {log.model_used.split('/').pop()}
          </span>
        )}

        {/* Elapsed */}
        <span className="text-[9px] text-jarvis-text-dim/40 shrink-0">
          {(log.elapsed_ms / 1000).toFixed(1)}s
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden border-t border-jarvis-border/20"
          >
            <pre className="px-4 py-3 text-[10px] font-mono text-jarvis-text-dim whitespace-pre-wrap break-words max-h-60 overflow-y-auto bg-jarvis-bg/40">
              {log.content}
            </pre>
            {log.error && (
              <div className="px-4 py-2 text-[10px] font-mono text-jarvis-red bg-jarvis-red/5 border-t border-jarvis-red/20">
                {log.error}
              </div>
            )}
          </m.div>
        )}
      </AnimatePresence>
    </m.div>
  );
}

function ReviewIssueRow({ issue }: { issue: ReviewIssue }) {
  return (
    <div className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs font-mono ${SEVERITY_STYLES[issue.severity] ?? ''}`}>
      {issue.severity === 'error'
        ? <XCircle size={11} className="shrink-0 mt-0.5" />
        : issue.severity === 'warning'
        ? <AlertTriangle size={11} className="shrink-0 mt-0.5" />
        : <Zap size={11} className="shrink-0 mt-0.5" />
      }
      <div className="flex-1">
        <span className="text-jarvis-text-bright">{issue.file}</span>
        {issue.line && <span className="text-jarvis-text-dim">:{issue.line}</span>}
        <span className="ml-2">{issue.message}</span>
      </div>
    </div>
  );
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center p-2 rounded-lg bg-jarvis-bg/60 border border-jarvis-border/20">
      <div className="text-jarvis-text-bright text-lg font-mono font-bold">{value}</div>
      <div className="text-jarvis-text-dim text-[9px] font-mono tracking-widest mt-0.5">{label}</div>
    </div>
  );
}
