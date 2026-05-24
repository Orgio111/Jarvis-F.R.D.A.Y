import { useState } from 'react';
import { m } from 'framer-motion';
import { Brain, Network, CheckCircle2, AlertCircle, Layers, GitBranch, BarChart3, Lightbulb, Zap, TrendingUp } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { cn } from '@/lib/utils';

const STRATEGIES = [
  { id: 'chain_of_thought', label: 'Chain of Thought', icon: GitBranch, desc: 'Step-by-step logical reasoning', color: 'from-cyan-500/20 to-blue-600/10 border-cyan-500/30' },
  { id: 'tree_of_thought', label: 'Tree of Thought', icon: Layers, desc: 'Multi-branch exploration', color: 'from-violet-500/20 to-purple-600/10 border-violet-500/30' },
  { id: 'self_verification', label: 'Self-Verify', icon: CheckCircle2, desc: 'Generate then verify', color: 'from-emerald-500/20 to-green-600/10 border-emerald-500/30' },
  { id: 'decomposition', label: 'Decompose', icon: Network, desc: 'Break into sub-problems', color: 'from-amber-500/20 to-orange-600/10 border-amber-500/30' },
  { id: 'multi_perspective', label: 'Debate', icon: Lightbulb, desc: 'Multiple viewpoints', color: 'from-rose-500/20 to-pink-600/10 border-rose-500/30' },
];

const RECENT_TRACES = [
  { id: 't1', query: 'Design authentication system architecture', strategy: 'tree_of_thought', confidence: 0.87, duration: '1.2s' },
  { id: 't2', query: 'Debug memory leak in agent service', strategy: 'decomposition', confidence: 0.92, duration: '0.8s' },
  { id: 't3', query: 'Evaluate tradeoffs: microservices vs monolith', strategy: 'multi_perspective', confidence: 0.79, duration: '1.5s' },
];

export function ReasoningPanel() {
  const [query, setQuery] = useState('');
  const [selectedStrategy, setSelectedStrategy] = useState('chain_of_thought');
  const [isReasoning, setIsReasoning] = useState(false);

  const handleReason = async () => {
    if (!query.trim()) return;
    setIsReasoning(true);
    // Simulate reasoning
    await new Promise(r => setTimeout(r, 1500));
    setIsReasoning(false);
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <SectionHeader
        title="Cognitive Reasoning"
        subtitle="Tree-of-thought, self-verification & debate engine"
        icon={Brain}
        actions={
          <NeonBadge color="violet">v2 Advanced</NeonBadge>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Left: Strategy Selection & Input */}
        <div className="xl:col-span-2 space-y-4">
          {/* Strategy Selector */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Strategy</span>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {STRATEGIES.map((strategy) => (
                <m.button
                  key={strategy.id}
                  onClick={() => setSelectedStrategy(strategy.id)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-lg border bg-gradient-to-br transition-all duration-200 text-left',
                    selectedStrategy === strategy.id
                      ? 'border-jarvis-cyan/40 bg-jarvis-cyan/5 shadow-lg shadow-black/20'
                      : 'border-jarvis-border/20 hover:border-jarvis-border/40',
                    strategy.color
                  )}
                >
                  <strategy.icon size={16} className="mt-0.5 shrink-0 text-jarvis-text-dim/60" />
                  <div>
                    <div className="text-xs font-mono text-jarvis-text">{strategy.label}</div>
                    <div className="text-[10px] font-mono text-jarvis-text-dim/40 mt-0.5">{strategy.desc}</div>
                  </div>
                </m.button>
              ))}
            </div>
          </GlassPanel>

          {/* Query Input */}
          <GlassPanel className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Query</span>
              <NeonBadge color={selectedStrategy === 'tree_of_thought' ? 'violet' : 'cyan'}>
                {STRATEGIES.find(s => s.id === selectedStrategy)?.label}
              </NeonBadge>
            </div>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter a complex question or problem to reason about..."
              rows={4}
              className="w-full bg-jarvis-bg-2/30 border border-jarvis-border/20 rounded-lg p-3 text-xs font-mono text-jarvis-text placeholder:text-jarvis-text-dim/20 outline-none focus:border-jarvis-cyan/40 focus:ring-1 focus:ring-jarvis-cyan/20 transition-all resize-none"
            />
            <div className="flex items-center justify-between mt-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/30">{query.length} characters</span>
              <button
                onClick={handleReason}
                disabled={!query.trim() || isReasoning}
                className={cn(
                  'px-5 py-2 text-xs font-mono rounded-lg transition-all duration-200 flex items-center gap-2',
                  isReasoning
                    ? 'bg-cyan-500/20 text-cyan-400 cursor-wait'
                    : 'btn-cockpit-primary'
                )}
              >
                {isReasoning ? (
                  <>
                    <m.div className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} />
                    Reasoning...
                  </>
                ) : (
                  <>
                    <Zap size={14} />
                    Reason
                  </>
                )}
              </button>
            </div>
          </GlassPanel>

          {/* Results Area */}
          <GlassPanel className="flex-1 p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Results</span>
            {isReasoning ? (
              <div className="flex items-center justify-center h-32">
                <div className="text-center">
                  <m.div
                    className="w-8 h-8 border-2 border-violet-400 border-t-transparent rounded-full mx-auto"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
                  />
                  <p className="text-xs font-mono text-jarvis-text-dim/50 mt-3">Exploring reasoning paths...</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-32">
                <div className="text-center">
                  <Brain size={32} className="mx-auto text-jarvis-text-dim/20 mb-2" />
                  <p className="text-xs font-mono text-jarvis-text-dim/30">Enter a query and select a strategy to begin</p>
                </div>
              </div>
            )}
          </GlassPanel>
        </div>

        {/* Right: History & Metrics */}
        <div className="xl:col-span-1 space-y-4">
          {/* Recent Traces */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Recent Traces</span>
            <div className="mt-3 space-y-2">
              {RECENT_TRACES.map((trace) => (
                <m.div
                  key={trace.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg border border-jarvis-border/20 bg-jarvis-bg-2/20 hover:border-jarvis-border/40 transition-all cursor-pointer"
                >
                  <div className="text-[11px] font-mono text-jarvis-text leading-tight line-clamp-2">{trace.query}</div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[9px] font-mono text-jarvis-cyan uppercase">{trace.strategy.replace(/_/g, ' ')}</span>
                    <span className="text-[9px] font-mono text-jarvis-text-dim/40">·</span>
                    <span className="text-[9px] font-mono text-emerald-400/60">{(trace.confidence * 100).toFixed(0)}%</span>
                    <span className="text-[9px] font-mono text-jarvis-text-dim/40">·</span>
                    <span className="text-[9px] font-mono text-jarvis-text-dim/40">{trace.duration}</span>
                  </div>
                </m.div>
              ))}
            </div>
          </GlassPanel>

          {/* Stats */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Stats</span>
            <div className="mt-3 space-y-3">
              {[
                { label: 'Avg Confidence', value: '84%', icon: TrendingUp, color: 'text-emerald-400' },
                { label: 'Traces Today', value: '24', icon: BarChart3, color: 'text-cyan-400' },
                { label: 'Avg Duration', value: '1.1s', icon: Zap, color: 'text-amber-400' },
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
        </div>
      </div>
    </div>
  );
}
