import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { Workflow, Plus, Play, Save, Trash2, GripVertical, ChevronRight, Settings2, Pause, CheckCircle2 } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { cn } from '@/lib/utils';

interface WorkflowNode {
  id: string;
  type: 'trigger' | 'llm' | 'tool' | 'agent' | 'code' | 'output' | 'condition' | 'delay';
  label: string;
  status: 'idle' | 'running' | 'completed' | 'error';
}

const NODE_PALETTE: { type: WorkflowNode['type']; label: string; color: string }[] = [
  { type: 'trigger', label: 'Trigger', color: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30' },
  { type: 'llm', label: 'LLM Call', color: 'from-cyan-500/20 to-cyan-600/10 border-cyan-500/30' },
  { type: 'tool', label: 'Tool', color: 'from-violet-500/20 to-violet-600/10 border-violet-500/30' },
  { type: 'agent', label: 'Agent', color: 'from-amber-500/20 to-amber-600/10 border-amber-500/30' },
  { type: 'code', label: 'Code', color: 'from-blue-500/20 to-blue-600/10 border-blue-500/30' },
  { type: 'condition', label: 'Condition', color: 'from-rose-500/20 to-rose-600/10 border-rose-500/30' },
  { type: 'delay', label: 'Delay', color: 'from-slate-500/20 to-slate-600/10 border-slate-500/30' },
  { type: 'output', label: 'Output', color: 'from-green-500/20 to-green-600/10 border-green-500/30' },
];

const DEFAULT_WORKFLOWS = [
  { id: 'wf-1', name: 'Daily Code Review', nodes: 5, status: 'active' as const, lastRun: '2h ago' },
  { id: 'wf-2', name: 'Research & Summarize', nodes: 3, status: 'draft' as const, lastRun: '1d ago' },
  { id: 'wf-3', name: 'DevOps Pipeline Monitor', nodes: 7, status: 'running' as const, lastRun: 'now' },
];

export function WorkflowPanel() {
  const [workflows] = useState(DEFAULT_WORKFLOWS);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showPalette, setShowPalette] = useState(true);

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <SectionHeader
        title="Workflow Builder"
        subtitle="Visual AI automation pipelines"
        icon={Workflow}
        actions={
          <button className="btn-cockpit-primary px-4 py-1.5 text-xs flex items-center gap-2">
            <Plus size={14} />
            New Workflow
          </button>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Node Palette */}
        <AnimatePresence>
          {showPalette && (
            <m.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="xl:col-span-1 space-y-3"
            >
              <GlassPanel className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Node Types</span>
                  <button onClick={() => setShowPalette(false)} className="text-jarvis-text-dim/30 hover:text-jarvis-cyan text-xs">Hide</button>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {NODE_PALETTE.map((node) => (
                    <m.button
                      key={node.type}
                      whileHover={{ scale: 1.03 }}
                      whileTap={{ scale: 0.97 }}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-lg border bg-gradient-to-br text-xs font-mono transition-all duration-200',
                        'hover:shadow-lg hover:shadow-black/20',
                        node.color,
                        'text-jarvis-text-dim hover:text-jarvis-text'
                      )}
                      draggable
                    >
                      <GripVertical size={12} className="opacity-30" />
                      {node.label}
                    </m.button>
                  ))}
                </div>
              </GlassPanel>

              {/* Workflow Info */}
              <GlassPanel className="p-4">
                <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Tips</span>
                <ul className="mt-2 space-y-1.5 text-[11px] font-mono text-jarvis-text-dim/70">
                  <li className="flex items-center gap-2"><ChevronRight size={10} className="text-jarvis-cyan" />Drag nodes to canvas</li>
                  <li className="flex items-center gap-2"><ChevronRight size={10} className="text-jarvis-cyan" />Connect by dragging edge</li>
                  <li className="flex items-center gap-2"><ChevronRight size={10} className="text-jarvis-cyan" />Double-click to configure</li>
                </ul>
              </GlassPanel>
            </m.div>
          )}
        </AnimatePresence>

        {/* Canvas */}
        <div className={cn('xl:col-span-2', !showPalette && 'xl:col-span-3')}>
          <GlassPanel className="h-full flex flex-col">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-jarvis-border/20">
              <div className="flex items-center gap-2">
                {!showPalette && (
                  <button onClick={() => setShowPalette(true)} className="btn-cockpit-ghost px-2 py-1 text-xs">Show Palette</button>
                )}
                <NeonBadge color="cyan">Draft</NeonBadge>
              </div>
              <div className="flex items-center gap-2">
                <button className="btn-cockpit-ghost px-3 py-1 text-xs flex items-center gap-1.5"><Save size={12} />Save</button>
                <button className="btn-cockpit-primary px-3 py-1 text-xs flex items-center gap-1.5"><Play size={12} />Run</button>
              </div>
            </div>

            {/* Canvas Area */}
            <div className="flex-1 relative overflow-hidden">
              <div className="absolute inset-4 rounded-xl border-2 border-dashed border-jarvis-border/20 flex items-center justify-center">
                <div className="text-center">
                  <Workflow size={40} className="mx-auto text-jarvis-text-dim/20 mb-3" />
                  <p className="text-xs font-mono text-jarvis-text-dim/40">Drag nodes here to build your workflow</p>
                  <p className="text-[10px] font-mono text-jarvis-text-dim/20 mt-1">Connect them with edges to create automation pipelines</p>
                </div>
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>

      {/* Workflow List */}
      <GlassPanel className="p-4">
        <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Saved Workflows</span>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3">
          {workflows.map((wf) => (
            <m.button
              key={wf.id}
              onClick={() => setSelectedId(wf.id)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={cn(
                'flex items-center justify-between p-3 rounded-lg border transition-all duration-200 text-left',
                selectedId === wf.id
                  ? 'border-jarvis-cyan/40 bg-jarvis-cyan/5'
                  : 'border-jarvis-border/20 bg-jarvis-bg-2/30 hover:border-jarvis-border/40'
              )}
            >
              <div>
                <div className="text-xs font-mono text-jarvis-text">{wf.name}</div>
                <div className="text-[10px] font-mono text-jarvis-text-dim/40 mt-0.5">{wf.nodes} nodes · {wf.lastRun}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn(
                  'w-1.5 h-1.5 rounded-full',
                  wf.status === 'active' && 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.5)]',
                  wf.status === 'draft' && 'bg-amber-400 shadow-[0_0_6px_rgba(251,191,36,0.5)]',
                  wf.status === 'running' && 'bg-cyan-400 shadow-[0_0_6px_rgba(0,212,255,0.5)] animate-pulse',
                )} />
                <span className="text-[10px] font-mono text-jarvis-text-dim/40">{wf.status}</span>
              </div>
            </m.button>
          ))}
        </div>
      </GlassPanel>
    </div>
  );
}
