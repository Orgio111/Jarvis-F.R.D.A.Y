import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { History, Play, Trash2, Clock, MessageSquare, Workflow, Bot, Tag, ChevronRight, X } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { cn } from '@/lib/utils';
import {
  useReplaySessions,
  useReplaySession,
  useDeleteReplaySession,
  type ReplaySession,
  type ReplayEvent,
} from './useSessionReplay';

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDuration(s: number): string {
  if (s < 60) return `${s.toFixed(0)}s`;
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}m ${sec}s`;
}

function formatTs(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

function sessionTypeIcon(t: string) {
  if (t === 'workflow') return <Workflow size={13} />;
  if (t === 'agent_run') return <Bot size={13} />;
  return <MessageSquare size={13} />;
}

function eventKindColor(kind: string): string {
  switch (kind) {
    case 'user_message':   return 'text-jarvis-cyan';
    case 'agent_message':  return 'text-jarvis-green';
    case 'tool_call':      return 'text-jarvis-yellow';
    case 'tool_result':    return 'text-jarvis-text-dim';
    case 'approval_request': return 'text-orange-400';
    case 'approval_response': return 'text-purple-400';
    case 'error':          return 'text-jarvis-red';
    default:               return 'text-jarvis-text-dim';
  }
}

// ── Event row ─────────────────────────────────────────────────────────────────

function EventRow({ event, index }: { event: ReplayEvent; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div
      className="border-b border-jarvis-border/30 cursor-pointer hover:bg-white/5 transition-colors"
      onClick={() => setOpen(o => !o)}
    >
      <div className="flex items-center gap-3 px-3 py-2 text-xs">
        <span className="text-jarvis-text-dim w-6 text-right">{index + 1}</span>
        <span className={cn('font-mono w-36 shrink-0', eventKindColor(event.kind))}>
          {event.kind}
        </span>
        {event.model_used && (
          <span className="text-jarvis-text-dim/60 text-[10px] shrink-0">[{event.model_used}]</span>
        )}
        {event.duration_ms > 0 && (
          <span className="text-jarvis-text-dim/50 text-[10px] ml-auto">{event.duration_ms.toFixed(0)}ms</span>
        )}
      </div>
      <AnimatePresence>
        {open && (
          <m.pre
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="bg-black/30 text-[10px] text-jarvis-text-dim font-mono px-4 py-2 overflow-x-auto"
          >
            {JSON.stringify(event.data, null, 2)}
          </m.pre>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Session detail panel ──────────────────────────────────────────────────────

function SessionDetail({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const { data, isLoading } = useReplaySession(sessionId);

  return (
    <GlassPanel className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b border-jarvis-border/30">
        <SectionHeader icon={Play} title={data?.title ?? 'Session'} subtitle="Event replay" />
        <button onClick={onClose} className="text-jarvis-text-dim hover:text-white">
          <X size={16} />
        </button>
      </div>

      {isLoading && (
        <div className="flex-1 flex items-center justify-center text-jarvis-text-dim text-sm">
          Loading…
        </div>
      )}

      {data && (
        <div className="flex-1 overflow-y-auto">
          {/* Summary row */}
          <div className="flex gap-4 px-4 py-3 border-b border-jarvis-border/30 text-xs text-jarvis-text-dim flex-wrap">
            <span className="flex items-center gap-1"><Clock size={12} />{formatDuration(data.duration_s)}</span>
            <span>{data.event_count} events</span>
            <span>{formatTs(data.started_at)}</span>
            {Object.entries(data.model_summary).map(([m, c]) => (
              <NeonBadge key={m} label={`${m}: ${c}`} color="cyan" />
            ))}
          </div>

          {/* Events */}
          <div className="divide-y divide-jarvis-border/20">
            {data.events.map((evt, i) => (
              <EventRow key={evt.event_id} event={evt} index={i} />
            ))}
          </div>
        </div>
      )}
    </GlassPanel>
  );
}

// ── Session card ──────────────────────────────────────────────────────────────

function SessionCard({
  session,
  selected,
  onSelect,
  onDelete,
}: {
  session: ReplaySession;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
}) {
  return (
    <m.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'border rounded-lg p-3 cursor-pointer transition-all',
        selected
          ? 'border-jarvis-cyan/60 bg-jarvis-cyan/5'
          : 'border-jarvis-border/40 hover:border-jarvis-border/70 hover:bg-white/5',
      )}
      onClick={onSelect}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-jarvis-cyan">{sessionTypeIcon(session.session_type)}</span>
          <span className="text-sm font-medium truncate">{session.title}</span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <CockpitButton
            size="xs"
            variant="ghost"
            onClick={e => { e.stopPropagation(); onDelete(); }}
            icon={Trash2}
            className="opacity-40 hover:opacity-100 hover:text-jarvis-red"
          />
          <ChevronRight size={14} className="text-jarvis-text-dim" />
        </div>
      </div>

      <div className="flex items-center gap-3 mt-1.5 text-[11px] text-jarvis-text-dim">
        <span className="flex items-center gap-1"><Clock size={10} />{formatDuration(session.duration_s)}</span>
        <span>{session.event_count} events</span>
        <NeonBadge label={session.session_type} color="dim" />
      </div>

      {session.tags.length > 0 && (
        <div className="flex gap-1 mt-1.5 flex-wrap">
          {session.tags.map(t => (
            <span key={t} className="flex items-center gap-0.5 text-[10px] text-jarvis-text-dim bg-white/5 rounded px-1.5 py-0.5">
              <Tag size={9} />{t}
            </span>
          ))}
        </div>
      )}

      <div className="text-[10px] text-jarvis-text-dim/50 mt-1">{formatTs(session.started_at)}</div>
    </m.div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SessionReplayPage() {
  const [filter, setFilter] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<string | null>(null);
  const { data, isLoading } = useReplaySessions(filter);
  const deleteSession = useDeleteReplaySession();

  const sessions = data?.sessions ?? [];

  const filters = [
    { label: 'All', value: undefined },
    { label: 'Chat', value: 'chat' },
    { label: 'Workflow', value: 'workflow' },
    { label: 'Agent Run', value: 'agent_run' },
  ];

  return (
    <div className="flex h-full gap-4 p-4">
      {/* Left: list */}
      <div className="w-80 shrink-0 flex flex-col gap-3">
        <GlassPanel className="p-4">
          <SectionHeader icon={History} title="Session Replay" subtitle={`${sessions.length} sessions`} />

          {/* Filters */}
          <div className="flex gap-1 mt-3 flex-wrap">
            {filters.map(f => (
              <button
                key={String(f.value)}
                onClick={() => setFilter(f.value)}
                className={cn(
                  'text-xs px-2 py-1 rounded border transition-colors',
                  filter === f.value
                    ? 'border-jarvis-cyan text-jarvis-cyan bg-jarvis-cyan/10'
                    : 'border-jarvis-border/40 text-jarvis-text-dim hover:border-jarvis-border',
                )}
              >
                {f.label}
              </button>
            ))}
          </div>
        </GlassPanel>

        <div className="flex-1 overflow-y-auto flex flex-col gap-2">
          {isLoading && (
            <div className="text-center text-jarvis-text-dim text-sm py-8">Loading sessions…</div>
          )}
          {!isLoading && sessions.length === 0 && (
            <div className="text-center text-jarvis-text-dim text-sm py-8">
              No sessions recorded yet.<br />
              <span className="text-xs opacity-60">Sessions are captured automatically during chat and workflow runs.</span>
            </div>
          )}
          {sessions.map(s => (
            <SessionCard
              key={s.session_id}
              session={s}
              selected={selected === s.session_id}
              onSelect={() => setSelected(s.session_id)}
              onDelete={() => deleteSession.mutate(s.session_id)}
            />
          ))}
        </div>
      </div>

      {/* Right: detail */}
      <div className="flex-1">
        {selected ? (
          <SessionDetail sessionId={selected} onClose={() => setSelected(null)} />
        ) : (
          <GlassPanel className="h-full flex items-center justify-center">
            <div className="text-center text-jarvis-text-dim">
              <History size={48} className="mx-auto mb-3 opacity-20" />
              <p className="text-sm">Select a session to replay</p>
            </div>
          </GlassPanel>
        )}
      </div>
    </div>
  );
}
