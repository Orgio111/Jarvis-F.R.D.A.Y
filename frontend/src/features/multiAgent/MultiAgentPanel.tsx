import { useState, useEffect, useRef, useCallback } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { StatusDot } from '@/components/ui/StatusDot';
import {
  Network,
  Play,
  StopCircle,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Terminal,
  Users,
  Layers,
  Radio,
  Cpu,
  Trash2,
  BookOpen,
} from 'lucide-react';
// GitBranch intentionally unused — reserved for future flow view
import { cn } from '@/lib/utils';

const API = 'http://localhost:8100';

// ── Types ────────────────────────────────────────────────────────────────────

interface AgentInfo {
  agent_id: string;
  role?: string;
  status?: string;
  current_task?: string;
  task_count?: number;
  created_at?: string;
}

interface SystemStatus {
  status: string;
  active_sessions?: number;
  total_agents?: number;
  patterns?: string[];
}

interface StreamMessage {
  id: string;
  type: 'agent_log' | 'task_complete' | 'error' | 'system' | 'raw';
  content: string;
  timestamp: string;
  agentId?: string;
}

interface BlackboardEntry {
  key: string;
  value: unknown;
  timestamp?: string;
}

type Pattern = 'auto' | 'parallel' | 'chain' | 'hub_spoke';

// ── API helpers ───────────────────────────────────────────────────────────────

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Main Panel ────────────────────────────────────────────────────────────────

export function MultiAgentPanel() {
  const [task, setTask] = useState('');
  const [pattern, setPattern] = useState<Pattern>('auto');
  const [maxAgents, setMaxAgents] = useState(3);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [messages, setMessages] = useState<StreamMessage[]>([]);
  const [blackboard, setBlackboard] = useState<BlackboardEntry[]>([]);

  const [showBlackboard, setShowBlackboard] = useState(false);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);

  const sseRef = useRef<EventSource | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  // ── Fetch system status ──────────────────────────────────────────────────

  const refreshStatus = useCallback(async () => {
    try {
      const s = await fetchJson<SystemStatus>('/multi-agent/status');
      setStatus(s);
    } catch {
      // silently fail
    }
  }, []);

  const refreshAgents = useCallback(async (sid: string) => {
    try {
      const data = await fetchJson<{ agents: AgentInfo[] }>(`/multi-agent/agents?session_id=${sid}`);
      setAgents(data.agents ?? []);
    } catch {
      setAgents([]);
    }
  }, []);

  const refreshBlackboard = useCallback(async (sid: string) => {
    try {
      const data = await fetchJson<{ messages: BlackboardEntry[] }>(`/multi-agent/history?topic=${sid}&limit=50`);
      setBlackboard(data.messages ?? []);
    } catch {
      setBlackboard([]);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    const id = setInterval(refreshStatus, 10_000);
    return () => clearInterval(id);
  }, [refreshStatus]);

  useEffect(() => {
    if (!sessionId) return;
    const id = setInterval(() => {
      refreshAgents(sessionId);
      refreshBlackboard(sessionId);
    }, 3000);
    return () => clearInterval(id);
  }, [sessionId, refreshAgents, refreshBlackboard]);

  // Auto-scroll log
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── SSE stream ───────────────────────────────────────────────────────────

  const startSSE = useCallback((sid: string) => {
    if (sseRef.current) {
      sseRef.current.close();
    }
    const es = new EventSource(`${API}/multi-agent/stream/${sid}`);
    sseRef.current = es;

    es.onmessage = (ev) => {
      try {
        const parsed = JSON.parse(ev.data);
        const msg: StreamMessage = {
          id: `${Date.now()}-${Math.random()}`,
          type: parsed.type ?? 'agent_log',
          content: parsed.content ?? parsed.message ?? JSON.stringify(parsed),
          timestamp: parsed.timestamp ?? new Date().toISOString(),
          agentId: parsed.agent_id,
        };
        setMessages((prev) => [...prev.slice(-500), msg]);
      } catch {
        setMessages((prev) => [
          ...prev.slice(-500),
          {
            id: `${Date.now()}-${Math.random()}`,
            type: 'raw',
            content: ev.data,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    };

    es.onerror = () => {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}`,
          type: 'system',
          content: 'SSE connection closed.',
          timestamp: new Date().toISOString(),
        },
      ]);
      es.close();
    };
  }, []);

  const stopSSE = useCallback(() => {
    sseRef.current?.close();
    sseRef.current = null;
  }, []);

  // ── Run task ─────────────────────────────────────────────────────────────

  const runTask = async () => {
    if (!task.trim()) return;
    setIsRunning(true);
    setMessages([]);
    setAgents([]);
    setBlackboard([]);

    try {
      const result = await postJson<{ session_id: string; status: string }>('/multi-agent/run', {
        task: task.trim(),
        pattern,
        max_agents: maxAgents,
        cleanup: false,
      });
      const sid = result.session_id;
      setSessionId(sid);
      startSSE(sid);
      await refreshAgents(sid);
      await refreshBlackboard(sid);

      setMessages((prev) => [
        ...prev,
        {
          id: 'init',
          type: 'system',
          content: `Session started: ${sid} — pattern: ${pattern}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setMessages([{
        id: 'err',
        type: 'error',
        content: String(err),
        timestamp: new Date().toISOString(),
      }]);
      setIsRunning(false);
    }
  };

  const stopTask = () => {
    stopSSE();
    setIsRunning(false);
  };

  const clearSession = () => {
    stopSSE();
    setIsRunning(false);
    setSessionId(null);
    setMessages([]);
    setAgents([]);
    setBlackboard([]);
  };

  return (
    <div className="p-6 space-y-6 h-full overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <SectionHeader
          title="Multi-Agent System"
          subtitle="Coordinate intelligent agent networks for complex tasks"
          icon={Network}
        />
        <div className="flex items-center gap-2 flex-wrap">
          <NeonBadge color={status?.status === 'online' ? 'green' : 'red'} label={status?.status ?? 'unknown'} size="sm" />
          {status?.active_sessions !== undefined && (
            <NeonBadge color="cyan" label={`${status.active_sessions} sessions`} size="sm" />
          )}
          {status?.total_agents !== undefined && (
            <NeonBadge color="blue" label={`${status.total_agents} agents`} size="sm" />
          )}
        </div>
      </div>

      {/* Task Form */}
      <GlassPanel className="p-4 space-y-4">
        <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2">
          <Play size={12} />
          Run Multi-Agent Task
        </p>

        {/* Task input */}
        <div>
          <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Task Description</label>
          <textarea
            value={task}
            onChange={(e) => setTask(e.target.value)}
            rows={3}
            placeholder="Describe the complex task for the agent network..."
            className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text placeholder-jarvis-text-dim/30 focus:outline-none focus:border-jarvis-cyan/50 resize-none"
          />
        </div>

        {/* Config row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Pattern</label>
            <select
              value={pattern}
              onChange={(e) => setPattern(e.target.value as Pattern)}
              className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
            >
              <option value="auto">Auto</option>
              <option value="parallel">Parallel</option>
              <option value="chain">Chain</option>
              <option value="hub_spoke">Hub & Spoke</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Max Agents</label>
            <input
              type="number"
              min={1}
              max={10}
              value={maxAgents}
              onChange={(e) => setMaxAgents(Number(e.target.value))}
              className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
            />
          </div>
          <div className="sm:col-span-2 flex items-end gap-2">
            <CockpitButton
              icon={<Play size={14} />}
              onClick={runTask}
              variant="primary"
              size="sm"
              loading={isRunning}
              disabled={!task.trim() || isRunning}
              className="flex-1"
            >
              Run Task
            </CockpitButton>
            {isRunning && (
              <CockpitButton
                icon={<StopCircle size={14} />}
                onClick={stopTask}
                variant="ghost"
                size="sm"
              >
                Stop
              </CockpitButton>
            )}
            {(sessionId || messages.length > 0) && (
              <CockpitButton
                icon={<Trash2 size={14} />}
                onClick={clearSession}
                variant="ghost"
                size="sm"
              >
                Clear
              </CockpitButton>
            )}
          </div>
        </div>

        {/* Pattern description */}
        <PatternHint pattern={pattern} />
      </GlassPanel>

      {/* Active Agents */}
      <AnimatePresence>
        {agents.length > 0 && (
          <m.div
            key="agents"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
          >
            <GlassPanel className="p-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2">
                  <Users size={12} />
                  Active Agents ({agents.length})
                </p>
                {sessionId && (
                  <CockpitButton
                    icon={<RefreshCw size={12} />}
                    onClick={() => refreshAgents(sessionId)}
                    variant="ghost"
                    size="sm"
                  >
                    Refresh
                  </CockpitButton>
                )}
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {agents.map((agent) => (
                  <AgentCard
                    key={agent.agent_id}
                    agent={agent}
                    expanded={expandedAgent === agent.agent_id}
                    onToggle={() => setExpandedAgent(
                      expandedAgent === agent.agent_id ? null : agent.agent_id
                    )}
                  />
                ))}
              </div>
            </GlassPanel>
          </m.div>
        )}
      </AnimatePresence>

      {/* SSE Log + Blackboard side by side */}
      <div className={cn('grid gap-4', showBlackboard ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1')}>
        {/* Stream Log */}
        <GlassPanel className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2">
              <Terminal size={12} />
              Agent Stream Log
              {isRunning && (
                <m.span
                  className="inline-block w-1.5 h-1.5 rounded-full bg-jarvis-green"
                  animate={{ opacity: [1, 0.2, 1] }}
                  transition={{ duration: 1.2, repeat: Infinity }}
                />
              )}
            </p>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-jarvis-text-dim/40">{messages.length} events</span>
              <CockpitButton
                icon={<BookOpen size={12} />}
                onClick={() => setShowBlackboard(!showBlackboard)}
                variant="ghost"
                size="sm"
              >
                {showBlackboard ? 'Hide BB' : 'Blackboard'}
              </CockpitButton>
            </div>
          </div>

          <div className="h-72 overflow-y-auto scrollbar-thin bg-jarvis-bg-3/30 rounded-lg p-3 space-y-1 font-mono text-xs">
            {messages.length === 0 ? (
              <p className="text-jarvis-text-dim/30 italic">Waiting for stream events...</p>
            ) : (
              messages.map((msg) => (
                <StreamLogLine key={msg.id} msg={msg} />
              ))
            )}
            <div ref={logEndRef} />
          </div>
        </GlassPanel>

        {/* Blackboard */}
        <AnimatePresence>
          {showBlackboard && (
            <m.div
              key="blackboard"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <GlassPanel className="p-4 space-y-3 h-full">
                <div className="flex items-center justify-between">
                  <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider flex items-center gap-2">
                    <Layers size={12} />
                    Blackboard / History
                  </p>
                  {sessionId && (
                    <CockpitButton
                      icon={<RefreshCw size={12} />}
                      onClick={() => refreshBlackboard(sessionId)}
                      variant="ghost"
                      size="sm"
                    >
                      Refresh
                    </CockpitButton>
                  )}
                </div>
                <div className="h-72 overflow-y-auto scrollbar-thin bg-jarvis-bg-3/30 rounded-lg p-3 space-y-2">
                  {blackboard.length === 0 ? (
                    <p className="text-jarvis-text-dim/30 text-xs italic font-mono">No blackboard entries yet.</p>
                  ) : (
                    blackboard.map((entry, i) => (
                      <BlackboardRow key={i} entry={entry} />
                    ))
                  )}
                </div>
              </GlassPanel>
            </m.div>
          )}
        </AnimatePresence>
      </div>

      {/* System Info */}
      {status?.patterns && (
        <GlassPanel className="p-4">
          <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider mb-3 flex items-center gap-2">
            <Radio size={12} />
            Supported Patterns
          </p>
          <div className="flex flex-wrap gap-2">
            {status.patterns.map((p) => (
              <span
                key={p}
                className="px-2.5 py-1 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/20 text-jarvis-cyan text-[10px] font-mono uppercase tracking-wider"
              >
                {p.replace('_', ' ')}
              </span>
            ))}
          </div>
        </GlassPanel>
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PatternHint({ pattern }: { pattern: Pattern }) {
  const hints: Record<Pattern, string> = {
    auto: 'System auto-selects the best coordination pattern based on task complexity.',
    parallel: 'Multiple agents work simultaneously on independent sub-tasks.',
    chain: 'Agents work sequentially, each building on the previous result.',
    hub_spoke: 'A coordinator agent delegates to specialized worker agents.',
  };
  return (
    <p className="text-[10px] font-mono text-jarvis-text-dim/50 leading-relaxed">
      <span className="text-jarvis-cyan/60 uppercase">{pattern.replace('_', ' ')}: </span>
      {hints[pattern]}
    </p>
  );
}

function AgentCard({
  agent,
  expanded,
  onToggle,
}: {
  agent: AgentInfo;
  expanded: boolean;
  onToggle: () => void;
}) {
  const isActive = agent.status === 'active' || agent.status === 'busy' || agent.status === 'working';

  return (
    <m.div
      layout
      className="bg-jarvis-bg-3/40 border border-jarvis-border/30 rounded-lg overflow-hidden cursor-pointer hover:border-jarvis-cyan/30 transition-colors"
      onClick={onToggle}
    >
      <div className="px-3 py-2 flex items-center gap-2">
        <StatusDot status={isActive ? 'active' : 'idle'} />
        <Cpu size={12} className="text-jarvis-cyan/60 shrink-0" />
        <span className="text-xs font-mono text-jarvis-text truncate flex-1">
          {agent.role ?? 'Agent'}
        </span>
        <span className="text-[10px] font-mono text-jarvis-text-dim/40 shrink-0">
          #{agent.agent_id.slice(-6)}
        </span>
        {expanded ? (
          <ChevronDown size={12} className="text-jarvis-text-dim/40 shrink-0" />
        ) : (
          <ChevronRight size={12} className="text-jarvis-text-dim/40 shrink-0" />
        )}
      </div>
      <AnimatePresence>
        {expanded && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 space-y-1.5 border-t border-jarvis-border/20 pt-2">
              <InfoRow label="ID" value={agent.agent_id} />
              {agent.status && <InfoRow label="Status" value={agent.status} />}
              {agent.task_count !== undefined && (
                <InfoRow label="Tasks" value={String(agent.task_count)} />
              )}
              {agent.current_task && (
                <InfoRow label="Task" value={agent.current_task} truncate />
              )}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </m.div>
  );
}

function InfoRow({
  label,
  value,
  truncate,
}: {
  label: string;
  value: string;
  truncate?: boolean;
}) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-[10px] font-mono text-jarvis-text-dim/50 w-12 shrink-0">{label}</span>
      <span className={cn('text-[10px] font-mono text-jarvis-text break-all', truncate && 'truncate')}>
        {value}
      </span>
    </div>
  );
}

function StreamLogLine({ msg }: { msg: StreamMessage }) {
  const colors: Record<string, string> = {
    agent_log: 'text-jarvis-text',
    task_complete: 'text-jarvis-green',
    error: 'text-jarvis-red',
    system: 'text-jarvis-cyan/70',
    raw: 'text-jarvis-text-dim/70',
  };

  const prefixes: Record<string, string> = {
    agent_log: '◦',
    task_complete: '✓',
    error: '✗',
    system: '⟩',
    raw: '·',
  };

  const time = new Date(msg.timestamp).toLocaleTimeString('en', { hour12: false });

  return (
    <div className={cn('flex items-start gap-2 leading-relaxed', colors[msg.type] ?? 'text-jarvis-text')}>
      <span className="text-jarvis-text-dim/30 shrink-0 w-16 text-[10px]">{time}</span>
      <span className="shrink-0 text-[10px]">{prefixes[msg.type] ?? '·'}</span>
      {msg.agentId && (
        <span className="text-jarvis-blue/60 shrink-0 text-[10px]">[{msg.agentId.slice(-6)}]</span>
      )}
      <span className="break-all text-[11px]">{msg.content}</span>
    </div>
  );
}

function BlackboardRow({ entry }: { entry: BlackboardEntry }) {
  const val =
    typeof entry.value === 'string'
      ? entry.value
      : JSON.stringify(entry.value, null, 2);

  return (
    <div className="border border-jarvis-border/20 rounded-lg p-2 space-y-1">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-mono text-jarvis-cyan/80 truncate">{entry.key}</span>
        {entry.timestamp && (
          <span className="text-[9px] font-mono text-jarvis-text-dim/30 shrink-0">
            {new Date(entry.timestamp).toLocaleTimeString('en', { hour12: false })}
          </span>
        )}
      </div>
      <pre className="text-[10px] font-mono text-jarvis-text-dim/70 whitespace-pre-wrap break-all max-h-20 overflow-y-auto scrollbar-thin">
        {val}
      </pre>
    </div>
  );
}

// Re-export for lazy import
export { MultiAgentPanel as default };
