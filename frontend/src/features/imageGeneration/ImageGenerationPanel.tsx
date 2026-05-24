import { useState } from 'react';
import { m } from 'framer-motion';
import { Image, Sparkles, Download, Sliders, RefreshCw, History, Square, Wand2 } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { cn } from '@/lib/utils';

const GENERATIONS = [
  { id: 'g1', prompt: 'Cyberpunk city with neon lights', style: 'cinematic', size: '1024×1024', time: '2.3s ago' },
  { id: 'g2', prompt: 'Futuristic AI server room', style: 'concept', size: '1024×1024', time: '5.1s ago' },
  { id: 'g3', prompt: 'Abstract neural network visualization', style: 'abstract', size: '1024×1024', time: '12s ago' },
];

export function ImageGenerationPanel() {
  const [prompt, setPrompt] = useState('');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [steps, setSteps] = useState(4);
  const [guidance, setGuidance] = useState(7.5);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    await new Promise(r => setTimeout(r, 2500));
    setGenerating(false);
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <SectionHeader
        title="Image Generation"
        subtitle="Ultra-fast Sana-powered local image synthesis"
        icon={Image}
        actions={
          <NeonBadge color="violet">
            <Sparkles size={10} className="mr-1" />
            Sana 600M
          </NeonBadge>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Left: Controls */}
        <div className="xl:col-span-2 space-y-4">
          {/* Prompt Input */}
          <GlassPanel className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Prompt</span>
              <button className="text-[10px] font-mono text-jarvis-text-dim/30 hover:text-jarvis-cyan flex items-center gap-1">
                <Wand2 size={10} /> Enhance
              </button>
            </div>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe the image you want to generate..."
              rows={3}
              className="w-full bg-jarvis-bg-2/30 border border-jarvis-border/20 rounded-lg p-3 text-xs font-mono text-jarvis-text placeholder:text-jarvis-text-dim/20 outline-none focus:border-jarvis-cyan/40 focus:ring-1 focus:ring-jarvis-cyan/20 transition-all resize-none"
            />
            <input
              type="text"
              value={negativePrompt}
              onChange={(e) => setNegativePrompt(e.target.value)}
              placeholder="Negative prompt (things to avoid)..."
              className="w-full mt-2 bg-jarvis-bg-2/30 border border-jarvis-border/20 rounded-lg p-2.5 text-[11px] font-mono text-jarvis-text-dim/70 placeholder:text-jarvis-text-dim/20 outline-none focus:border-jarvis-cyan/40 transition-all"
            />
          </GlassPanel>

          {/* Controls Row */}
          <GlassPanel className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-[9px] font-mono text-jarvis-text-dim/40 uppercase tracking-[0.1em]">Steps</label>
                <div className="flex items-center gap-2 mt-1">
                  <input
                    type="range"
                    min={1}
                    max={32}
                    value={steps}
                    onChange={(e) => setSteps(Number(e.target.value))}
                    className="flex-1 accent-jarvis-cyan"
                  />
                  <span className="text-xs font-mono text-jarvis-text-dim/70 w-6 text-right">{steps}</span>
                </div>
              </div>
              <div>
                <label className="text-[9px] font-mono text-jarvis-text-dim/40 uppercase tracking-[0.1em]">Guidance</label>
                <div className="flex items-center gap-2 mt-1">
                  <input
                    type="range"
                    min={1}
                    max={15}
                    step={0.5}
                    value={guidance}
                    onChange={(e) => setGuidance(Number(e.target.value))}
                    className="flex-1 accent-jarvis-cyan"
                  />
                  <span className="text-xs font-mono text-jarvis-text-dim/70 w-6 text-right">{guidance}</span>
                </div>
              </div>
              <div>
                <label className="text-[9px] font-mono text-jarvis-text-dim/40 uppercase tracking-[0.1em]">Size</label>
                <select className="w-full mt-1 bg-jarvis-bg-2/50 border border-jarvis-border/20 rounded-lg px-2 py-1.5 text-xs font-mono text-jarvis-text outline-none">
                  <option>1024×1024</option>
                  <option>1024×768</option>
                  <option>768×1024</option>
                  <option>512×512</option>
                </select>
              </div>
              <div>
                <label className="text-[9px] font-mono text-jarvis-text-dim/40 uppercase tracking-[0.1em]">Count</label>
                <select className="w-full mt-1 bg-jarvis-bg-2/50 border border-jarvis-border/20 rounded-lg px-2 py-1.5 text-xs font-mono text-jarvis-text outline-none">
                  <option>1</option>
                  <option>2</option>
                  <option>4</option>
                </select>
              </div>
            </div>
          </GlassPanel>

          {/* Generation Result */}
          <GlassPanel className="flex-1 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Output</span>
              <button
                onClick={handleGenerate}
                disabled={!prompt.trim() || generating}
                className={cn(
                  'px-5 py-2 text-xs font-mono rounded-lg transition-all duration-200 flex items-center gap-2',
                  generating
                    ? 'bg-violet-500/20 text-violet-400 cursor-wait'
                    : 'btn-cockpit-primary'
                )}
              >
                {generating ? (
                  <><m.div className="w-3 h-3 border-2 border-violet-400 border-t-transparent rounded-full" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} /> Generating...</>
                ) : (
                  <><Sparkles size={14} /> Generate</>
                )}
              </button>
            </div>

            {generating ? (
              <div className="flex items-center justify-center h-48">
                <div className="text-center">
                  <m.div
                    className="w-12 h-12 border-2 border-violet-400/50 border-t-violet-400 rounded-full mx-auto"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  />
                  <p className="text-xs font-mono text-jarvis-text-dim/50 mt-3">Generating with Sana (4 steps)...</p>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-48 rounded-xl border-2 border-dashed border-jarvis-border/10">
                <div className="text-center">
                  <Image size={40} className="mx-auto text-jarvis-text-dim/20 mb-2" />
                  <p className="text-xs font-mono text-jarvis-text-dim/30">Your generated image will appear here</p>
                </div>
              </div>
            )}
          </GlassPanel>
        </div>

        {/* Right: History */}
        <div className="xl:col-span-1 space-y-4">
          {/* Recent Generations */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Recent</span>
            <div className="mt-3 space-y-2">
              {GENERATIONS.map((gen) => (
                <m.div
                  key={gen.id}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 rounded-lg border border-jarvis-border/20 bg-jarvis-bg-2/20 hover:border-jarvis-border/40 transition-all cursor-pointer"
                >
                  <div className="text-[11px] font-mono text-jarvis-text leading-tight line-clamp-2">{gen.prompt}</div>
                  <div className="flex items-center gap-2 mt-2 text-[9px] font-mono text-jarvis-text-dim/40">
                    <span>{gen.style}</span>
                    <span>·</span>
                    <span>{gen.size}</span>
                    <span>·</span>
                    <span>{gen.time}</span>
                  </div>
                </m.div>
              ))}
            </div>
          </GlassPanel>

          {/* Model Info */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Model</span>
            <div className="mt-3 space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-jarvis-text-dim/60">Architecture</span>
                <span className="text-jarvis-text">Sana 600M</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-jarvis-text-dim/60">Speed</span>
                <span className="text-emerald-400">Ultra-fast</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-jarvis-text-dim/60">Resolution</span>
                <span className="text-jarvis-text">1024×1024</span>
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-jarvis-text-dim/60">Steps</span>
                <span className="text-jarvis-text">4-8 (fast) / 16-32 (quality)</span>
              </div>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
