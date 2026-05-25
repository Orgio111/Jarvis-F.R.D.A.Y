import { useState } from 'react';
import { m } from 'framer-motion';
import { Dna, GitCompare, TrendingUp, FileText, Plus, CheckCircle2, AlertCircle, Target } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { cn } from '@/lib/utils';

const TEMPLATES = [
  { id: 't1', name: 'Code Review Prompt', version: 3, score: 0.87, usage: 42, successRate: 0.91 },
  { id: 't2', name: 'Architecture Design', version: 2, score: 0.82, usage: 28, successRate: 0.85 },
  { id: 't3', name: 'Debug Assistant', version: 5, score: 0.94, usage: 67, successRate: 0.96 },
  { id: 't4', name: 'Research Summary', version: 1, score: 0.73, usage: 15, successRate: 0.78 },
];

const MUTATION_TYPES = [
  { id: 'rewrite', label: 'Rewrite', desc: 'Complete rewrite preserving intent' },
  { id: 'expand', label: 'Expand', desc: 'Add context and examples' },
  { id: 'contract', label: 'Contract', desc: 'Condense to essentials' },
  { id: 'rephrase', label: 'Rephrase', desc: 'Change communication style' },
  { id: 'restructure', label: 'Restructure', desc: 'Explicit section format' },
];

const EVOLUTION_HISTORY = [
  { gen: 1, before: 0.65, after: 0.72, improved: true },
  { gen: 2, before: 0.72, after: 0.78, improved: true },
  { gen: 3, before: 0.78, after: 0.82, improved: true },
];

export function PromptMutationPanel() {
  const [selectedMutation, setSelectedMutation] = useState('rewrite');
  const [evolving, setEvolving] = useState(false);

  const handleEvolve = async () => {
    setEvolving(true);
    await new Promise(r => setTimeout(r, 2000));
    setEvolving(false);
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <SectionHeader
        title="Prompt Mutation Engine"
        subtitle="Self-improving prompts through evolutionary loops"
        icon={Dna}
        actions={
          <button className="btn-cockpit-primary px-4 py-1.5 text-xs flex items-center gap-2">
            <Plus size={14} />
            New Template
          </button>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Left: Templates & Evolution */}
        <div className="xl:col-span-2 space-y-4">
          {/* Templates */}
          <GlassPanel className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Prompt Templates</span>
              <NeonBadge color="cyan">{TEMPLATES.length} registered</NeonBadge>
            </div>
            <div className="space-y-2">
              {TEMPLATES.map((tmpl) => (
                <m.div
                  key={tmpl.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-center justify-between p-3 rounded-lg border border-jarvis-border/20 bg-jarvis-bg-2/20 hover:border-jarvis-border/40 transition-all cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center">
                      <FileText size={14} className="text-cyan-400" />
                    </div>
                    <div>
                      <div className="text-xs font-mono text-jarvis-text">{tmpl.name}</div>
                      <div className="text-[10px] font-mono text-jarvis-text-dim/40">v{tmpl.version} · {tmpl.usage} uses</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-xs font-mono font-bold text-jarvis-text">{(tmpl.score * 100).toFixed(0)}%</div>
                      <div className="text-[9px] font-mono text-jarvis-text-dim/40">Score</div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-mono text-emerald-400">{(tmpl.successRate * 100).toFixed(0)}%</div>
                      <div className="text-[9px] font-mono text-jarvis-text-dim/40">Success</div>
                    </div>
                  </div>
                </m.div>
              ))}
            </div>
          </GlassPanel>

          {/* Mutation Types & Controls */}
          <GlassPanel className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Mutation Strategy</span>
              <button
                onClick={handleEvolve}
                disabled={evolving}
                className={cn(
                  'px-4 py-1.5 text-xs flex items-center gap-2 rounded-lg transition-all font-mono',
                  evolving
                    ? 'bg-amber-500/20 text-amber-400 cursor-wait'
                    : 'btn-cockpit-primary'
                )}
              >
                {evolving ? (
                  <><m.div className="w-3 h-3 border-2 border-amber-400 border-t-transparent rounded-full" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} /> Evolving...</>
                ) : (
                  <><Dna size={14} /> Run Evolution</>
                )}
              </button>
            </div>
            <div className="grid grid-cols-5 gap-2">
              {MUTATION_TYPES.map((mt) => (
                <m.button
                  key={mt.id}
                  onClick={() => setSelectedMutation(mt.id)}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className={cn(
                    'p-3 rounded-lg border transition-all duration-200 text-center',
                    selectedMutation === mt.id
                      ? 'border-cyan-500/40 bg-cyan-500/10'
                      : 'border-jarvis-border/20 hover:border-jarvis-border/40'
                  )}
                >
                  <div className={cn(
                    'text-xs font-mono',
                    selectedMutation === mt.id ? 'text-cyan-400' : 'text-jarvis-text-dim'
                  )}>
                    {mt.label}
                  </div>
                  <div className="text-[9px] font-mono text-jarvis-text-dim/40 mt-1">{mt.desc}</div>
                </m.button>
              ))}
            </div>
          </GlassPanel>

          {/* Evolution Results */}
          <GlassPanel className="flex-1 p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Evolution History</span>
            <div className="mt-3 space-y-2">
              {evolving ? (
                <div className="flex items-center justify-center h-24">
                  <div className="text-center">
                    <m.div
                      className="w-6 h-6 border-2 border-amber-400/50 border-t-amber-400 rounded-full mx-auto"
                      animate={{ rotate: 360 }}
                      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    />
                    <p className="text-xs font-mono text-jarvis-text-dim/50 mt-2">Mutating prompts across generations...</p>
                  </div>
                </div>
              ) : (
                EVOLUTION_HISTORY.map((gen) => (
                  <div key={gen.gen} className="flex items-center justify-between p-3 rounded-lg border border-jarvis-border/20 bg-jarvis-bg-2/20">
                    <div className="flex items-center gap-3">
                      <span className="text-xs font-mono font-bold text-jarvis-text-dim/70">Gen {gen.gen}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-jarvis-text-dim/50">{gen.before.toFixed(2)}</span>
                        <TrendingUp size={12} className={gen.improved ? 'text-emerald-400' : 'text-rose-400'} />
                        <span className="text-xs font-mono text-emerald-400">{gen.after.toFixed(2)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {gen.improved ? (
                        <CheckCircle2 size={12} className="text-emerald-400" />
                      ) : (
                        <AlertCircle size={12} className="text-amber-400" />
                      )}
                      <span className="text-[10px] font-mono text-jarvis-text-dim/40">
                        {gen.improved ? `+${((gen.after - gen.before) * 100).toFixed(0)}%` : 'No improvement'}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </GlassPanel>
        </div>

        {/* Right: Stats & Info */}
        <div className="xl:col-span-1 space-y-4">
          {/* Stats */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Stats</span>
            <div className="mt-3 space-y-3">
              {[
                { label: 'Avg Score', value: '0.84', icon: Target, color: 'text-emerald-400' },
                { label: 'Best Score', value: '0.94', icon: TrendingUp, color: 'text-cyan-400' },
                { label: 'Total Mutations', value: '152', icon: GitCompare, color: 'text-violet-400' },
                { label: 'Improvement Rate', value: '76%', icon: CheckCircle2, color: 'text-amber-400' },
              ].map((stat) => (
                <div key={stat.label} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <stat.icon size={12} className={cn('shrink-0', stat.color)} />
                    <span className="text-[10px] font-mono text-jarvis-text-dim/60">{stat.label}</span>
                  </div>
                  <span className={cn('text-xs font-mono font-bold', stat.color)}>{stat.value}</span>
                </div>
              ))}
            </div>
          </GlassPanel>

          {/* Info */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">How It Works</span>
            <div className="mt-3 space-y-2 text-[10px] font-mono text-jarvis-text-dim/50">
              <p className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-cyan-500/10 text-cyan-400 flex items-center justify-center shrink-0 text-[9px]">1</span>
                Register a prompt template
              </p>
              <p className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-violet-500/10 text-violet-400 flex items-center justify-center shrink-0 text-[9px]">2</span>
                Generate mutated variants
              </p>
              <p className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-amber-500/10 text-amber-400 flex items-center justify-center shrink-0 text-[9px]">3</span>
                Evaluate & score each variant
              </p>
              <p className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0 text-[9px]">4</span>
                Keep the best performer
              </p>
              <p className="flex items-start gap-2">
                <span className="w-4 h-4 rounded-full bg-rose-500/10 text-rose-400 flex items-center justify-center shrink-0 text-[9px]">5</span>
                Repeat for N generations
              </p>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
