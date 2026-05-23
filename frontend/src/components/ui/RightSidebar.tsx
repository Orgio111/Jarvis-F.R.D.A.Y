import { useState, useEffect } from 'react';
import { m } from 'framer-motion';

// ─── AI Agent data ──────────────────────────────────────────────────────────

interface Agent {
  name: string;
  status: 'active' | 'idle' | 'busy';
  subtitle: string;
}

const AGENTS: Agent[] = [
  { name: 'Planner',    status: 'active', subtitle: 'Strategy & decomposition' },
  { name: 'Researcher', status: 'active', subtitle: 'Web & knowledge search' },
  { name: 'Coder',      status: 'busy',   subtitle: 'Code generation' },
  { name: 'Executor',   status: 'idle',   subtitle: 'Command execution' },
  { name: 'Memory',     status: 'active', subtitle: 'Vector recall' },
];

const STATUS_COLORS: Record<Agent['status'], string> = {
  active: 'bg-jarvis-green',
  busy:   'bg-jarvis-yellow',
  idle:   'bg-jarvis-text-dim',
};

const STATUS_PULSE: Record<Agent['status'], string> = {
  active: 'animate-pulse',
  busy:   'animate-pulse',
  idle:   '',
};

// ─── System logs ────────────────────────────────────────────────────────────

interface LogEntry {
  time: string;
  message: string;
}

const INITIAL_LOGS: LogEntry[] = [
  { time: '14:52', message: 'System initialized' },
  { time: '14:53', message: 'AI agents online' },
  { time: '14:54', message: 'Diagnostics complete' },
  { time: '14:55', message: 'Threat level LOW' },
];

// ─── RightSidebar ───────────────────────────────────────────────────────────

export function RightSidebar() {
  return (
    <aside className="w-[280px] shrink-0 flex flex-col border-l overflow-y-auto bg-jarvis-bg/90 backdrop-blur-md"
      style={{ borderColor: 'var(--jarvis-border)' }}
    >
      {/* AI Agents */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--jarvis-border)' }}>
        <h3 className="text-jarvis-cyan text-xs font-mono font-semibold tracking-[0.2em] mb-3 uppercase">
          AI Agents
        </h3>
        <div className="space-y-1.5">
          {AGENTS.map((agent, i) => (
            <m.div
              key={agent.name}
              className="flex items-center gap-3 px-3 py-2 rounded-lg cursor-default group"
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              whileHover={{ x: 4, transition: { type: 'spring', stiffness: 300, damping: 25 } }}
            >
              <span className={`relative w-2 h-2 rounded-full ${STATUS_COLORS[agent.status]} ${STATUS_PULSE[agent.status]} shrink-0 group-hover:scale-125 transition-transform duration-200`} />
              <div className="flex-1 min-w-0 p-1.5 rounded-lg transition-all duration-200 group-hover:bg-jarvis-bg-3/50 group-hover:shadow-[inset_0_1px_0_rgba(0,212,255,0.03)]">
                <p className="text-xs font-mono text-jarvis-text-bright group-hover:text-jarvis-cyan transition-colors duration-200">
                  {agent.name}
                </p>
                <p className="text-[10px] font-mono text-jarvis-text-dim/60 truncate">
                  {agent.subtitle}
                </p>
              </div>
              <m.span
                className={`text-[9px] font-mono uppercase tracking-wider ${
                  agent.status === 'active' ? 'text-jarvis-green' :
                  agent.status === 'busy' ? 'text-jarvis-yellow' :
                  'text-jarvis-text-dim/40'
                }`}
                whileHover={{ scale: 1.05 }}
              >
                {agent.status}
              </m.span>
            </m.div>
          ))}
        </div>
      </div>

      {/* Active Tasks */}
      <div className="p-4 border-b" style={{ borderColor: 'var(--jarvis-border)' }}>
        <h3 className="text-jarvis-cyan text-xs font-mono font-semibold tracking-[0.2em] mb-3 uppercase">
          Active Tasks
        </h3>
        <div className="space-y-3">
          <TaskBar label="Pipeline build" pct={72} color="bg-jarvis-cyan" />
          <TaskBar label="Vector indexing" pct={45} color="bg-jarvis-blue" />
          <TaskBar label="Model loading" pct={90} color="bg-jarvis-yellow" />
          <TaskBar label="System scan" pct={30} color="bg-jarvis-green" />
        </div>
      </div>

      {/* System Logs */}
      <div className="p-4 flex-1">
        <h3 className="text-jarvis-cyan text-xs font-mono font-semibold tracking-[0.2em] mb-3 uppercase">
          System Logs
        </h3>
        <div className="space-y-1.5">
          <SystemLogs />
        </div>
      </div>
    </aside>
  );
}

// ─── Task Bar ───────────────────────────────────────────────────────────────

function TaskBar({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <m.div
      className="space-y-1 group/task"
      whileHover={{ x: 2, transition: { type: 'spring', stiffness: 300, damping: 25 } }}
    >
      <div className="flex justify-between text-[11px] font-mono">
        <span className="text-jarvis-text-dim/80 group-hover/task:text-jarvis-cyan/80 transition-colors duration-200">{label}</span>
        <span className="text-jarvis-text-dim/60 group-hover/task:text-jarvis-cyan/60 transition-colors duration-200">{pct}%</span>
      </div>
      <div className="h-1.5 bg-jarvis-bg-3/60 rounded-full overflow-hidden group-hover/task:h-2 transition-all duration-200">
        <m.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.2 }}
        />
      </div>
    </m.div>
  );
}

// ─── System Logs ────────────────────────────────────────────────────────────

function SystemLogs() {
  const [logs, setLogs] = useState<LogEntry[]>(INITIAL_LOGS);

  useEffect(() => {
    const id = setInterval(() => {
      const now = new Date();
      const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
      const messages = [
        'Health check passed',
        'Memory synced',
        'Agent heartbeat OK',
        'GPU temp stable',
        'Cache refreshed',
        'No anomalies detected',
        'Ready for commands',
      ];
      const msg = messages[Math.floor(Math.random() * messages.length)];
      setLogs((prev) => [...prev.slice(-19), { time, message: msg }]);
    }, 4000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-1">
      {logs.map((log, i) => (
        <m.div
          key={`${log.time}-${log.message}-${i}`}
          className="flex items-start gap-2 text-[11px] font-mono leading-relaxed group/log"
          initial={i === logs.length - 1 ? { opacity: 0, x: -4 } : undefined}
          animate={i === logs.length - 1 ? { opacity: 1, x: 0 } : undefined}
          transition={{ duration: 0.3 }}
          whileHover={{ x: 3, transition: { type: 'spring', stiffness: 300, damping: 25 } }}
        >
          <span className="text-jarvis-green/60 shrink-0 group-hover/log:text-jarvis-cyan transition-colors duration-200">[{log.time}]</span>
          <span className="text-jarvis-green/40 group-hover/log:text-jarvis-text-bright transition-colors duration-200">{log.message}</span>
        </m.div>
      ))}
    </div>
  );
}
