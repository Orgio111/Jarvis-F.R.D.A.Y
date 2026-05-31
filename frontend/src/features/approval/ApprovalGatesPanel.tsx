import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { ShieldAlert, CheckCircle2, XCircle, Clock, AlertTriangle, Shield, History } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { cn } from '@/lib/utils';
import { usePendingApprovals, useApprovalHistory, useRespondApproval, type ApprovalRequest } from './useApprovalGates';

// ── Helpers ───────────────────────────────────────────────────────────────────

function riskColor(level: string): string {
  switch (level) {
    case 'critical': return 'text-red-400 border-red-500/50 bg-red-500/10';
    case 'high':     return 'text-orange-400 border-orange-500/50 bg-orange-500/10';
    case 'medium':   return 'text-yellow-400 border-yellow-500/50 bg-yellow-500/10';
    default:         return 'text-green-400 border-green-500/50 bg-green-500/10';
  }
}

function statusIcon(status: string) {
  switch (status) {
    case 'approved':      return <CheckCircle2 size={13} className="text-jarvis-green" />;
    case 'rejected':      return <XCircle size={13} className="text-jarvis-red" />;
    case 'timed_out':     return <Clock size={13} className="text-yellow-400" />;
    case 'auto_approved': return <CheckCircle2 size={13} className="text-jarvis-text-dim" />;
    default:              return <Clock size={13} className="text-jarvis-cyan animate-pulse" />;
  }
}

function formatTs(ts: number) {
  return new Date(ts * 1000).toLocaleTimeString();
}

// ── Pending gate card ─────────────────────────────────────────────────────────

function PendingGateCard({ req }: { req: ApprovalRequest }) {
  const [rejectReason, setRejectReason] = useState('');
  const [showReject, setShowReject] = useState(false);
  const respond = useRespondApproval();

  const approve = () => respond.mutate({ requestId: req.request_id, approved: true });
  const reject  = () => respond.mutate({ requestId: req.request_id, approved: false, reason: rejectReason });

  return (
    <m.div
      layout
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className={cn('border rounded-lg p-4', riskColor(req.risk_level))}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <ShieldAlert size={16} />
            <span className="font-semibold text-sm">{req.action}</span>
          </div>
          {req.description && (
            <p className="text-xs mt-1 opacity-80">{req.description}</p>
          )}
        </div>
        <NeonBadge label={req.risk_level.toUpperCase()} color={req.risk_level === 'critical' ? 'red' : req.risk_level === 'high' ? 'yellow' : 'cyan'} />
      </div>

      {/* Details */}
      {Object.keys(req.details).length > 0 && (
        <pre className="mt-2 bg-black/30 rounded p-2 text-[10px] font-mono overflow-x-auto max-h-24">
          {JSON.stringify(req.details, null, 2)}
        </pre>
      )}

      <div className="text-[10px] opacity-60 mt-2">{formatTs(req.created_at)}</div>

      {/* Reject input */}
      <AnimatePresence>
        {showReject && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-2"
          >
            <input
              className="w-full bg-black/40 border border-jarvis-border/50 rounded px-2 py-1 text-xs text-white"
              placeholder="Reason for rejection…"
              value={rejectReason}
              onChange={e => setRejectReason(e.target.value)}
            />
          </m.div>
        )}
      </AnimatePresence>

      {/* Actions */}
      <div className="flex gap-2 mt-3">
        <CockpitButton
          variant="primary"
          size="sm"
          icon={CheckCircle2}
          onClick={approve}
          disabled={respond.isPending}
          className="flex-1 bg-jarvis-green/20 border-jarvis-green/40 text-jarvis-green hover:bg-jarvis-green/30"
        >
          Approve
        </CockpitButton>

        {showReject ? (
          <CockpitButton
            variant="danger"
            size="sm"
            icon={XCircle}
            onClick={reject}
            disabled={respond.isPending}
            className="flex-1"
          >
            Confirm Reject
          </CockpitButton>
        ) : (
          <CockpitButton
            variant="ghost"
            size="sm"
            icon={XCircle}
            onClick={() => setShowReject(true)}
            className="flex-1 text-jarvis-red border-jarvis-red/30 hover:bg-jarvis-red/10"
          >
            Reject
          </CockpitButton>
        )}
      </div>
    </m.div>
  );
}

// ── History row ───────────────────────────────────────────────────────────────

function HistoryRow({ req }: { req: ApprovalRequest }) {
  return (
    <div className="flex items-center gap-3 py-2 px-3 border-b border-jarvis-border/20 text-xs">
      {statusIcon(req.status)}
      <span className="flex-1 truncate text-jarvis-text-dim">{req.action}</span>
      <NeonBadge label={req.risk_level} color="dim" />
      <span className="text-jarvis-text-dim/50 shrink-0">{formatTs(req.created_at)}</span>
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function ApprovalGatesPanel() {
  const [tab, setTab] = useState<'pending' | 'history'>('pending');
  const { data: pending = [], isLoading: pLoading } = usePendingApprovals();
  const { data: history = [], isLoading: hLoading } = useApprovalHistory();

  return (
    <GlassPanel className="flex flex-col h-full">
      <div className="p-4 border-b border-jarvis-border/30">
        <SectionHeader
          icon={Shield}
          title="Approval Gates"
          subtitle="Human-in-the-loop for critical actions"
        />

        {/* Tabs */}
        <div className="flex gap-2 mt-3">
          {(['pending', 'history'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                'text-xs px-3 py-1 rounded border transition-colors capitalize',
                tab === t
                  ? 'border-jarvis-cyan text-jarvis-cyan bg-jarvis-cyan/10'
                  : 'border-jarvis-border/40 text-jarvis-text-dim hover:border-jarvis-border',
              )}
            >
              {t}
              {t === 'pending' && pending.length > 0 && (
                <span className="ml-1.5 bg-jarvis-red text-white rounded-full text-[10px] px-1.5 py-0.5">
                  {pending.length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {tab === 'pending' && (
          <>
            {pLoading && <div className="text-center text-jarvis-text-dim text-sm py-8">Loading…</div>}
            {!pLoading && pending.length === 0 && (
              <div className="text-center text-jarvis-text-dim py-12">
                <CheckCircle2 size={36} className="mx-auto mb-3 opacity-20 text-jarvis-green" />
                <p className="text-sm">No pending approvals</p>
              </div>
            )}
            <AnimatePresence mode="popLayout">
              <div className="flex flex-col gap-3">
                {pending.map(req => (
                  <PendingGateCard key={req.request_id} req={req} />
                ))}
              </div>
            </AnimatePresence>
          </>
        )}

        {tab === 'history' && (
          <>
            {hLoading && <div className="text-center text-jarvis-text-dim text-sm py-8">Loading…</div>}
            {!hLoading && history.length === 0 && (
              <div className="text-center text-jarvis-text-dim py-8 text-sm">No history yet</div>
            )}
            <div className="divide-y divide-jarvis-border/20">
              {history.map(req => <HistoryRow key={req.request_id} req={req} />)}
            </div>
          </>
        )}
      </div>
    </GlassPanel>
  );
}
