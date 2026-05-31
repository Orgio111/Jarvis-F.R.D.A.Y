import { useState } from 'react';
import { m } from 'framer-motion';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useEvolutionStatus, useEvolutionTrials, useBestPractices, useProposeMutation, useRunTrial } from './useSelfEvolution';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { CockpitButton } from '@/components/ui/CockpitButton';
import { apiClient } from '@/lib/api/client';
import { Dna, TrendingUp, Target, FlaskConical, CheckCircle2, Sparkles, Lightbulb, ArrowUp, ArrowDown, ThumbsUp, ThumbsDown, Lightbulb as LightbulbIcon } from 'lucide-react';

const MUTATION_TYPES = [
  { value: 'prompt_strategy', label: 'Prompt Strategy' },
  { value: 'routing_decision', label: 'Routing Decision' },
  { value: 'workflow_pattern', label: 'Workflow Pattern' },
  { value: 'agent_config', label: 'Agent Config' },
  { value: 'model_selection', label: 'Model Selection' },
  { value: 'threshold_tuning', label: 'Threshold Tuning' },
  { value: 'parallelization', label: 'Parallelization' },
];

export function SelfEvolutionPanel() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'trials' | 'mutate'>('dashboard');
  const [mutType, setMutType] = useState('prompt_strategy');
  const [mutTarget, setMutTarget] = useState('');
  const [mutCurrentValue, setMutCurrentValue] = useState('');

  const { data: status } = useEvolutionStatus();
  const { data: trialsData } = useEvolutionTrials(20);
  const { data: bestPracticesData } = useBestPractices(10);

  // ── Self Improvement suggestions ──
  const { data: suggestionsData } = useQuery<{ suggestions: Array<{ id: string; title: string; description: string; targetArea: string; expectedImprovement: number; status: string }> }>({
    queryKey: ['self-improvement', 'suggestions'],
    queryFn: () => apiClient.get('/self-improvement/suggestions'),
    staleTime: 30_000,
    gcTime: 5 * 60_000,
  });
  const approveSuggestion = useMutation({
    mutationFn: (id: string) => apiClient.post(`/self-improvement/suggestions/${id}/approve`, {}),
  });
  const rejectSuggestion = useMutation({
    mutationFn: (id: string) => apiClient.post(`/self-improvement/suggestions/${id}/reject`, {}),
  });

  const proposeMut = useProposeMutation();
  const runTrial = useRunTrial();

  const trials = trialsData?.trials ?? [];
  const bestPractices = bestPracticesData?.bestPractices ?? [];
  const suggestions = suggestionsData?.suggestions ?? [];

  const handlePropose = () => {
    if (!mutTarget.trim()) return;
    proposeMut.mutate({
      mutationType: mutType,
      target: mutTarget,
      currentValue: mutCurrentValue || 'default',
    });
  };

  const improvedCount = status?.improvedTrials ?? 0;
  const totalCount = status?.totalTrials ?? 0;
  const improvementRate = status?.improvementRate ?? 0;

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <SectionHeader
            title="Self-Evolution Engine"
            subtitle="Continuous self-improvement through mutation, scoring, and reinforcement"
            icon={Dna}
          />
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <>
              <NeonBadge color={improvementRate > 0.5 ? 'green' : 'yellow'} label={`${(improvementRate * 100).toFixed(0)}% improved`} size="sm" />
              <NeonBadge color="cyan" label={`${totalCount} trials`} size="sm" />
            </>
          )}
        </div>
      </div>

      {/* Metric cards */}
      {status && (
        <div className="grid grid-cols-4 gap-4">
          <GlassPanel className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <FlaskConical size={14} className="text-jarvis-cyan" />
              <span className="text-[10px] font-mono text-jarvis-text-dim">Total Trials</span>
            </div>
            <p className="text-lg font-mono font-bold text-jarvis-text-bright">{totalCount}</p>
          </GlassPanel>
          <GlassPanel className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 size={14} className="text-jarvis-green" />
              <span className="text-[10px] font-mono text-jarvis-text-dim">Improved</span>
            </div>
            <p className="text-lg font-mono font-bold text-jarvis-green">{improvedCount}</p>
          </GlassPanel>
          <GlassPanel className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Target size={14} className="text-jarvis-purple" />
              <span className="text-[10px] font-mono text-jarvis-text-dim">Targets Tracked</span>
            </div>
            <p className="text-lg font-mono font-bold text-jarvis-purple">{status.targetsTracked}</p>
          </GlassPanel>
          <GlassPanel className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp size={14} className="text-jarvis-yellow" />
              <span className="text-[10px] font-mono text-jarvis-text-dim">Mutation Threshold</span>
            </div>
            <p className="text-lg font-mono font-bold text-jarvis-yellow">{status.autoMutateThreshold.toFixed(2)}</p>
          </GlassPanel>
        </div>
      )}

      {/* Mutation success rates */}
      {status && status.mutationSuccessRates && Object.keys(status.mutationSuccessRates).length > 0 && (
        <GlassPanel className="p-4">
          <p className="text-jarvis-cyan text-[10px] font-mono font-bold uppercase tracking-wider mb-3">Mutation Success Rates</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {Object.entries(status.mutationSuccessRates).map(([target, rate]) => (
              <div key={target} className="flex items-center gap-2">
                <div className="flex-1">
                  <p className="text-[10px] font-mono text-jarvis-text-dim/80 truncate">{target}</p>
                  <div className="h-1.5 bg-jarvis-bg-3/50 rounded-full overflow-hidden mt-1">
                    <div
                      className={`h-full rounded-full ${rate > 0.6 ? 'bg-jarvis-green' : rate > 0.3 ? 'bg-jarvis-yellow' : 'bg-jarvis-red'}`}
                      style={{ width: `${rate * 100}%` }}
                    />
                  </div>
                </div>
                <span className="text-xs font-mono text-jarvis-text-bright">{(rate * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </GlassPanel>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 border-b border-jarvis-border/20">
        {(['dashboard', 'suggestions', 'trials', 'mutate'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-xs font-mono tracking-wider transition-all duration-200 border-b-2 ${
              activeTab === tab
                ? 'text-jarvis-cyan border-jarvis-cyan'
                : 'text-jarvis-text-dim/60 hover:text-jarvis-text border-transparent'
            }`}
          >
            {tab === 'dashboard' ? 'Best Practices' : tab === 'suggestions' ? 'Suggestions' : tab === 'trials' ? 'Trials' : 'Mutate'}
          </button>
        ))}
      </div>

      {/* Best Practices Tab */}
      {activeTab === 'dashboard' && (
        <div className="space-y-2">
          {bestPractices.length === 0 && (
            <GlassPanel className="p-8 flex flex-col items-center justify-center gap-3">
              <Lightbulb size={32} className="text-jarvis-text-dim/30" />
              <p className="text-jarvis-text-dim text-xs font-mono">No best practices yet — run some trials first</p>
            </GlassPanel>
          )}
          {bestPractices.map((bp) => (
            <GlassPanel key={bp.trialId} className="p-3">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded-lg bg-jarvis-green/10 flex items-center justify-center">
                  <Sparkles size={14} className="text-jarvis-green" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-jarvis-text-bright truncate">{bp.target}</p>
                  <p className="text-[10px] font-mono text-jarvis-text-dim/60">{bp.mutationType.replace(/_/g, ' ')}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-mono font-bold text-jarvis-green">+{bp.improvementDelta}%</p>
                  <p className="text-[10px] font-mono text-jarvis-text-dim/60">{bp.originalComposite} → {bp.mutatedComposite}</p>
                </div>
              </div>
            </GlassPanel>
          ))}
        </div>
      )}

      {/* Suggestions Tab */}
      {activeTab === 'suggestions' && (
        <div className="space-y-2">
          {suggestions.length === 0 && (
            <GlassPanel className="p-8 flex flex-col items-center justify-center gap-3">
              <LightbulbIcon size={32} className="text-jarvis-text-dim/30" />
              <p className="text-jarvis-text-dim text-xs font-mono">No improvement suggestions yet</p>
            </GlassPanel>
          )}
          {suggestions.map((s) => (
            <GlassPanel key={s.id} className="p-4">
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-jarvis-yellow/10 flex items-center justify-center shrink-0 mt-0.5">
                  <LightbulbIcon size={14} className="text-jarvis-yellow" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono font-semibold text-jarvis-text-bright">{s.title}</span>
                    <NeonBadge color={s.status === 'pending' ? 'yellow' : s.status === 'approved' ? 'green' : 'dim'} label={s.status} size="sm" />
                  </div>
                  <p className="text-[11px] font-mono text-jarvis-text-dim/70 mb-1">{s.description}</p>
                  <div className="flex items-center gap-3 text-[10px] font-mono text-jarvis-text-dim/50">
                    <span>Target: {s.targetArea}</span>
                    <span className="text-jarvis-green">+{s.expectedImprovement}% expected</span>
                  </div>
                </div>
                {s.status === 'pending' && (
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      onClick={() => approveSuggestion.mutate(s.id)}
                      className="p-1.5 rounded-lg bg-jarvis-green/10 border border-jarvis-green/30 text-jarvis-green hover:bg-jarvis-green/20 transition-all"
                      title="Approve"
                    >
                      <ThumbsUp size={12} />
                    </button>
                    <button
                      onClick={() => rejectSuggestion.mutate(s.id)}
                      className="p-1.5 rounded-lg bg-jarvis-red/10 border border-jarvis-red/30 text-jarvis-red hover:bg-jarvis-red/20 transition-all"
                      title="Reject"
                    >
                      <ThumbsDown size={12} />
                    </button>
                  </div>
                )}
              </div>
            </GlassPanel>
          ))}
        </div>
      )}

      {/* Trials Tab */}
      {activeTab === 'trials' && (
        <div className="space-y-2">
          {trials.length === 0 && (
            <GlassPanel className="p-8 flex flex-col items-center justify-center gap-3">
              <FlaskConical size={32} className="text-jarvis-text-dim/30" />
              <p className="text-jarvis-text-dim text-xs font-mono">No evolution trials yet</p>
            </GlassPanel>
          )}
          {trials.map((trial) => (
            <GlassPanel key={trial.trialId} className="p-3">
              <div className="flex items-center gap-3">
                <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${trial.improved ? 'bg-jarvis-green/10' : 'bg-jarvis-red/10'}`}>
                  {trial.improved ? <ArrowUp size={14} className="text-jarvis-green" /> : <ArrowDown size={14} className="text-jarvis-red" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-mono text-jarvis-text-bright truncate">{trial.target}</p>
                  <p className="text-[10px] font-mono text-jarvis-text-dim/60">{trial.mutationType.replace(/_/g, ' ')}</p>
                </div>
                <div className="text-right">
                  <p className={`text-xs font-mono font-bold ${trial.improved ? 'text-jarvis-green' : 'text-jarvis-red'}`}>
                    {trial.improved ? '+' : ''}{trial.improvementDelta.toFixed(1)}%
                  </p>
                  {trial.originalScore && trial.mutatedScore && (
                    <p className="text-[10px] font-mono text-jarvis-text-dim/60">
                      {trial.originalScore.composite.toFixed(3)} → {trial.mutatedScore.composite.toFixed(3)}
                    </p>
                  )}
                </div>
              </div>
            </GlassPanel>
          ))}
        </div>
      )}

      {/* Mutate Tab */}
      {activeTab === 'mutate' && (
        <GlassPanel className="p-4 space-y-3">
          <p className="text-jarvis-cyan text-xs font-mono font-bold uppercase tracking-wider">Propose Mutation</p>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Mutation Type</label>
              <select
                value={mutType}
                onChange={(e) => setMutType(e.target.value)}
                className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
              >
                {MUTATION_TYPES.map(mt => (
                  <option key={mt.value} value={mt.value}>{mt.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Target</label>
              <input
                value={mutTarget}
                onChange={(e) => setMutTarget(e.target.value)}
                className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
                placeholder="e.g. system_prompt"
              />
            </div>
            <div>
              <label className="text-[10px] font-mono text-jarvis-text-dim/60 block mb-1">Current Value</label>
              <input
                value={mutCurrentValue}
                onChange={(e) => setMutCurrentValue(e.target.value)}
                className="w-full bg-jarvis-bg-3/50 border border-jarvis-border/30 rounded-lg px-3 py-2 text-xs font-mono text-jarvis-text focus:outline-none focus:border-jarvis-cyan/50"
                placeholder="current config"
              />
            </div>
          </div>
          <div className="flex justify-end">
            <CockpitButton
              icon={<FlaskConical size={14} />}
              onClick={handlePropose}
              size="sm"
              loading={proposeMut.isPending}
            >Propose Mutation</CockpitButton>
          </div>

          {/* Mutation result */}
          {(proposeMut.data as any) && (
            <m.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-3 rounded-lg bg-jarvis-green/5 border border-jarvis-green/20"
            >
              <p className="text-jarvis-green text-xs font-mono mb-1">Mutation proposed</p>
              <p className="text-[10px] font-mono text-jarvis-text-dim/80">
                Target: {(proposeMut.data as any)?.data?.target ?? '—'} → {(proposeMut.data as any)?.data?.mutatedValue ?? '—'}
              </p>
            </m.div>
          )}

          {/* Quick actions */}
          <div className="pt-3 border-t border-jarvis-border/20">
            <p className="text-[10px] font-mono text-jarvis-text-dim/60 mb-2">Quick Actions</p>
            <div className="flex gap-2">
              <CockpitButton
                icon={<FlaskConical size={12} />}
                onClick={() => runTrial.mutate({
                  mutationType: 'prompt_strategy',
                  target: 'system_prompt',
                  originalValue: 'be concise',
                  mutatedValue: 'be thorough',
                  correctness: 0.7,
                  completeness: 0.8,
                  efficiency: 0.6,
                  confidence: 0.75,
                  latencyMs: 1200,
                  cost: 0.002,
                })}
                size="sm"
                variant="ghost"
                loading={runTrial.isPending}
              >Run Sample Trial</CockpitButton>
            </div>
          </div>
        </GlassPanel>
      )}
    </div>
  );
}
