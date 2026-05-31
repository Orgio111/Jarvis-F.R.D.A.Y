import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import {
  X, Star, Zap, Clock, TrendingUp, GitBranch, Play, Pause,
  Loader2, ChevronRight, Code2, BarChart3, History, RefreshCw,
  CheckCircle, AlertTriangle,
} from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { NeonBadge } from '@/components/ui/NeonBadge';
import type { Skill } from './types';
import { useSkillMarketplace } from './useSkillMarketplace';

const AI_BASE = 'http://localhost:8100';

interface Props {
  skill: Skill;
  onClose: () => void;
  onRefresh: () => void;
}

type Tab = 'overview' | 'source' | 'stats' | 'history';

export function SkillDetailModal({ skill, onClose, onRefresh }: Props) {
  const [tab, setTab] = useState<Tab>('overview');
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [ratingStatus, setRatingStatus] = useState<'idle' | 'saving' | 'done'>('idle');
  const [evolveStatus, setEvolveStatus] = useState<'idle' | 'evolving' | 'done' | 'error'>('idle');
  const [evolveMsg, setEvolveMsg] = useState('');
  const { toggleSkill } = useSkillMarketplace();

  const trustColor =
    skill.trust_score >= 0.8 ? 'text-green-400' :
    skill.trust_score >= 0.5 ? 'text-jarvis-cyan' :
    skill.trust_score >= 0.3 ? 'text-yellow-400' : 'text-jarvis-red';

  const handleRate = async (stars: number) => {
    setRating(stars);
    setRatingStatus('saving');
    try {
      await fetch(`${AI_BASE}/marketplace/rate/${skill.skill_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating: stars }),
      });
      setRatingStatus('done');
      onRefresh();
      setTimeout(() => setRatingStatus('idle'), 2000);
    } catch {
      setRatingStatus('idle');
    }
  };

  const handleEvolve = async () => {
    setEvolveStatus('evolving');
    setEvolveMsg('Analyzing skill performance and generating improvements...');
    try {
      const res = await fetch(`${AI_BASE}/marketplace/evolve/${skill.skill_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      const data = await res.json();
      if (res.ok) {
        setEvolveStatus('done');
        setEvolveMsg(data.message ?? 'Evolution complete. New version registered.');
        onRefresh();
      } else {
        setEvolveStatus('error');
        setEvolveMsg(data.detail ?? 'Evolution failed.');
      }
    } catch {
      setEvolveStatus('error');
      setEvolveMsg('Network error during evolution.');
    }
  };

  const handleToggle = async () => {
    await toggleSkill(skill.skill_id, !skill.enabled);
    onRefresh();
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <BarChart3 size={12} /> },
    { id: 'source', label: 'Source', icon: <Code2 size={12} /> },
    { id: 'stats', label: 'Stats', icon: <TrendingUp size={12} /> },
    { id: 'history', label: 'History', icon: <History size={12} /> },
  ];

  return (
    <m.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <m.div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      <m.div
        className="relative z-10 w-full max-w-2xl max-h-[85vh] flex flex-col"
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 24, scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 320, damping: 28 }}
      >
        <GlassPanel className="flex flex-col overflow-hidden max-h-[85vh]">
          {/* Header */}
          <div className="flex items-start justify-between p-5 border-b border-jarvis-border/30 shrink-0">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-jarvis-cyan/10 border border-jarvis-cyan/20 flex items-center justify-center text-lg shrink-0">
                {skill.icon ?? '⚡'}
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <h2 className="text-jarvis-text-bright text-sm font-mono font-bold">{skill.name}</h2>
                  <NeonBadge color={skill.enabled ? 'cyan' : 'red'} size="sm">
                    {skill.enabled ? 'Active' : 'Disabled'}
                  </NeonBadge>
                  {skill.category && (
                    <NeonBadge color="blue" size="sm">{skill.category}</NeonBadge>
                  )}
                </div>
                <p className="text-jarvis-text-dim text-[10px] font-mono mt-1 max-w-md leading-relaxed">
                  {skill.description}
                </p>
                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-[10px] font-mono text-jarvis-text-dim/50">
                    ID: {skill.skill_id.slice(0, 12)}…
                  </span>
                  {skill.version && (
                    <span className="text-[10px] font-mono text-jarvis-text-dim/50 flex items-center gap-1">
                      <GitBranch size={9} /> v{skill.version}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-7 h-7 flex items-center justify-center rounded-lg text-jarvis-text-dim/40 hover:text-jarvis-red hover:bg-jarvis-red/10 transition-all duration-200 shrink-0"
            >
              <X size={14} />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 px-5 pt-3 shrink-0 border-b border-jarvis-border/20">
            {tabs.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-[10px] font-mono transition-all duration-200 border-b-2 ${
                  tab === t.id
                    ? 'text-jarvis-cyan border-jarvis-cyan bg-jarvis-cyan/5'
                    : 'text-jarvis-text-dim border-transparent hover:text-jarvis-text hover:bg-jarvis-bg-3/40'
                }`}
              >
                {t.icon}
                {t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 overflow-y-auto scrollbar-thin p-5">
            <AnimatePresence mode="wait">
              {tab === 'overview' && (
                <m.div
                  key="overview"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.15 }}
                  className="space-y-4"
                >
                  {/* Trust Score */}
                  <div className="p-4 rounded-xl bg-jarvis-bg-3/40 border border-jarvis-border/30">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-mono text-jarvis-text-dim uppercase tracking-widest">
                        Trust Score
                      </span>
                      <span className={`text-lg font-mono font-bold ${trustColor}`}>
                        {(skill.trust_score * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-jarvis-bg-3/80 rounded-full overflow-hidden">
                      <m.div
                        className={`h-full rounded-full ${
                          skill.trust_score >= 0.8 ? 'bg-green-400' :
                          skill.trust_score >= 0.5 ? 'bg-jarvis-cyan' :
                          skill.trust_score >= 0.3 ? 'bg-yellow-400' : 'bg-jarvis-red'
                        }`}
                        initial={{ width: 0 }}
                        animate={{ width: `${skill.trust_score * 100}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                      />
                    </div>
                    <div className="grid grid-cols-4 gap-2 mt-3">
                      {[
                        { label: 'Success', value: `${((skill.success_rate ?? 0) * 100).toFixed(0)}%` },
                        { label: 'Usage', value: skill.usage_count ?? 0 },
                        { label: 'Latency', value: skill.avg_latency_ms ? `${skill.avg_latency_ms.toFixed(0)}ms` : '—' },
                        { label: 'Rating', value: skill.avg_rating ? skill.avg_rating.toFixed(1) : '—' },
                      ].map((m) => (
                        <div key={m.label} className="text-center">
                          <div className="text-jarvis-text-bright text-xs font-mono font-bold">{m.value}</div>
                          <div className="text-jarvis-text-dim text-[9px] font-mono mt-0.5">{m.label}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Rate */}
                  <div className="p-4 rounded-xl bg-jarvis-bg-3/40 border border-jarvis-border/30">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono text-jarvis-text-dim uppercase tracking-widest">
                        Rate this skill
                      </span>
                      {ratingStatus === 'saving' && <Loader2 size={11} className="text-jarvis-cyan animate-spin" />}
                      {ratingStatus === 'done' && <CheckCircle size={11} className="text-green-400" />}
                    </div>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((s) => (
                        <button
                          key={s}
                          onClick={() => handleRate(s)}
                          onMouseEnter={() => setHoverRating(s)}
                          onMouseLeave={() => setHoverRating(0)}
                          className="transition-transform duration-100 hover:scale-125"
                        >
                          <Star
                            size={20}
                            className={`transition-colors duration-150 ${
                              s <= (hoverRating || rating)
                                ? 'text-yellow-400 fill-yellow-400'
                                : 'text-jarvis-border/60'
                            }`}
                          />
                        </button>
                      ))}
                      {rating > 0 && (
                        <span className="text-[10px] font-mono text-jarvis-text-dim ml-2">
                          {['', 'Poor', 'Fair', 'Good', 'Great', 'Excellent'][rating]}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Tags */}
                  {skill.tags && skill.tags.length > 0 && (
                    <div>
                      <div className="text-[10px] font-mono text-jarvis-text-dim uppercase tracking-widest mb-2">Tags</div>
                      <div className="flex flex-wrap gap-1.5">
                        {skill.tags.map((tag) => (
                          <span
                            key={tag}
                            className="px-2 py-0.5 rounded-full bg-jarvis-bg-3/60 border border-jarvis-border/40 text-[10px] font-mono text-jarvis-text-dim"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Evolve status feedback */}
                  <AnimatePresence>
                    {evolveStatus !== 'idle' && (
                      <m.div
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className={`p-3 rounded-lg border flex items-start gap-2 ${
                          evolveStatus === 'evolving' ? 'bg-jarvis-cyan/5 border-jarvis-cyan/20' :
                          evolveStatus === 'done' ? 'bg-green-500/5 border-green-500/20' :
                          'bg-jarvis-red/5 border-jarvis-red/20'
                        }`}
                      >
                        {evolveStatus === 'evolving' && <Loader2 size={12} className="text-jarvis-cyan mt-0.5 shrink-0 animate-spin" />}
                        {evolveStatus === 'done' && <CheckCircle size={12} className="text-green-400 mt-0.5 shrink-0" />}
                        {evolveStatus === 'error' && <AlertTriangle size={12} className="text-jarvis-red mt-0.5 shrink-0" />}
                        <p className={`text-[10px] font-mono ${
                          evolveStatus === 'evolving' ? 'text-jarvis-cyan' :
                          evolveStatus === 'done' ? 'text-green-400' : 'text-jarvis-red'
                        }`}>
                          {evolveMsg}
                        </p>
                      </m.div>
                    )}
                  </AnimatePresence>
                </m.div>
              )}

              {tab === 'source' && (
                <m.div
                  key="source"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.15 }}
                >
                  <div className="text-[10px] font-mono text-jarvis-text-dim uppercase tracking-widest mb-2">
                    Implementation Code
                  </div>
                  <div className="rounded-xl bg-black/40 border border-jarvis-border/30 overflow-auto max-h-80">
                    <pre className="p-4 text-[10px] font-mono text-jarvis-text leading-relaxed whitespace-pre-wrap break-words">
                      {skill.code ?? '# No source code available for this skill.'}
                    </pre>
                  </div>
                  {skill.trigger_patterns && skill.trigger_patterns.length > 0 && (
                    <div className="mt-4">
                      <div className="text-[10px] font-mono text-jarvis-text-dim uppercase tracking-widest mb-2">
                        Trigger Patterns
                      </div>
                      <div className="space-y-1">
                        {skill.trigger_patterns.map((p, i) => (
                          <div key={i} className="flex items-center gap-2">
                            <ChevronRight size={10} className="text-jarvis-cyan shrink-0" />
                            <code className="text-[10px] font-mono text-jarvis-text-dim">{p}</code>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </m.div>
              )}

              {tab === 'stats' && (
                <m.div
                  key="stats"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.15 }}
                  className="space-y-3"
                >
                  {[
                    { label: 'Total Executions', value: skill.usage_count ?? 0, icon: <Zap size={12} /> },
                    { label: 'Success Rate', value: `${((skill.success_rate ?? 0) * 100).toFixed(1)}%`, icon: <CheckCircle size={12} /> },
                    { label: 'Avg Latency', value: skill.avg_latency_ms ? `${skill.avg_latency_ms.toFixed(1)} ms` : '—', icon: <Clock size={12} /> },
                    { label: 'Average Rating', value: skill.avg_rating ? `${skill.avg_rating.toFixed(2)} / 5` : 'Unrated', icon: <Star size={12} /> },
                    { label: 'Trust Score', value: `${(skill.trust_score * 100).toFixed(1)}%`, icon: <TrendingUp size={12} /> },
                    { label: 'Version', value: `v${skill.version ?? 1}`, icon: <GitBranch size={12} /> },
                  ].map((row) => (
                    <div
                      key={row.label}
                      className="flex items-center justify-between p-3 rounded-lg bg-jarvis-bg-3/40 border border-jarvis-border/20"
                    >
                      <div className="flex items-center gap-2 text-jarvis-text-dim">
                        {row.icon}
                        <span className="text-[10px] font-mono">{row.label}</span>
                      </div>
                      <span className="text-xs font-mono font-bold text-jarvis-text-bright">{row.value}</span>
                    </div>
                  ))}
                </m.div>
              )}

              {tab === 'history' && (
                <m.div
                  key="history"
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 8 }}
                  transition={{ duration: 0.15 }}
                >
                  <div className="text-[10px] font-mono text-jarvis-text-dim uppercase tracking-widest mb-3">
                    Version Chain
                  </div>
                  <div className="space-y-2">
                    {/* Current */}
                    <div className="flex items-start gap-3 p-3 rounded-lg bg-jarvis-cyan/5 border border-jarvis-cyan/20">
                      <div className="w-5 h-5 rounded-full bg-jarvis-cyan/20 border border-jarvis-cyan/40 flex items-center justify-center shrink-0 mt-0.5">
                        <div className="w-1.5 h-1.5 rounded-full bg-jarvis-cyan" />
                      </div>
                      <div>
                        <div className="text-jarvis-cyan text-[10px] font-mono font-bold">
                          v{skill.version ?? 1} · Current
                        </div>
                        <div className="text-jarvis-text-dim text-[9px] font-mono mt-0.5">
                          ID: {skill.skill_id}
                        </div>
                        {skill.created_at && (
                          <div className="text-jarvis-text-dim/50 text-[9px] font-mono mt-0.5">
                            Created: {new Date(skill.created_at).toLocaleString()}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Previous version placeholder */}
                    {skill.previous_version_id ? (
                      <div className="flex items-start gap-3 p-3 rounded-lg bg-jarvis-bg-3/40 border border-jarvis-border/20">
                        <div className="w-5 h-5 rounded-full bg-jarvis-bg-3/80 border border-jarvis-border/40 flex items-center justify-center shrink-0 mt-0.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-jarvis-text-dim" />
                        </div>
                        <div>
                          <div className="text-jarvis-text-dim text-[10px] font-mono">
                            v{(skill.version ?? 1) - 1} · Deprecated
                          </div>
                          <div className="text-jarvis-text-dim/50 text-[9px] font-mono mt-0.5">
                            ID: {skill.previous_version_id}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-4 text-jarvis-text-dim/40 text-[10px] font-mono">
                        No previous versions
                      </div>
                    )}
                  </div>
                </m.div>
              )}
            </AnimatePresence>
          </div>

          {/* Footer actions */}
          <div className="flex items-center justify-between p-4 border-t border-jarvis-border/30 shrink-0">
            <div className="flex items-center gap-2">
              <CockpitButton
                variant={skill.enabled ? 'danger' : 'primary'}
                size="sm"
                onClick={handleToggle}
                icon={skill.enabled ? <Pause size={12} /> : <Play size={12} />}
              >
                {skill.enabled ? 'Disable' : 'Enable'}
              </CockpitButton>
            </div>

            <div className="flex items-center gap-2">
              <CockpitButton
                variant="ghost"
                size="sm"
                onClick={handleEvolve}
                disabled={evolveStatus === 'evolving'}
                icon={evolveStatus === 'evolving'
                  ? <Loader2 size={12} className="animate-spin" />
                  : <RefreshCw size={12} />
                }
              >
                {evolveStatus === 'evolving' ? 'Evolving…' : 'Evolve'}
              </CockpitButton>

              <CockpitButton variant="ghost" size="sm" onClick={onClose}>
                Close
              </CockpitButton>
            </div>
          </div>
        </GlassPanel>
      </m.div>
    </m.div>
  );
}
