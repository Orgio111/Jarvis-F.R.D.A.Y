import { useState } from 'react';
import { m } from 'framer-motion';
import { Radio, Activity, Shield, Zap, CheckCircle2, RefreshCw, Server } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { cn } from '@/lib/utils';

const MOCK_PROVIDERS = [
  { name: 'OpenRouter Free', baseUrl: 'https://openrouter.ai/api/v1', available: true, free: true, latency: 180, score: 92, models: 42, capabilities: ['chat', 'code', 'vision'] },
  { name: 'NVIDIA NIM', baseUrl: 'https://integrate.api.nvidia.com/v1', available: true, free: false, latency: 95, score: 88, models: 28, capabilities: ['chat', 'code'] },
  { name: 'Groq Free', baseUrl: 'https://api.groq.com/openai/v1', available: true, free: true, latency: 220, score: 78, models: 8, capabilities: ['chat', 'code'] },
  { name: 'Ollama Local', baseUrl: 'http://localhost:11434/v1', available: false, free: true, latency: 0, score: 0, models: 0, capabilities: [] },
  { name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', available: true, free: false, latency: 310, score: 72, models: 6, capabilities: ['chat', 'code'] },
  { name: 'Together AI', baseUrl: 'https://api.together.xyz/v1', available: true, free: false, latency: 260, score: 65, models: 15, capabilities: ['chat', 'image'] },
];

export function ProviderDiscoveryPanel() {
  const [scanning, setScanning] = useState(false);
  const [monitoring, setMonitoring] = useState(false);

  const handleScan = async () => {
    setScanning(true);
    await new Promise(r => setTimeout(r, 2000));
    setScanning(false);
  };

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <SectionHeader
        title="Provider Discovery"
        subtitle="Automatic Free-LLM-API discovery & health monitoring"
        icon={Radio}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={handleScan}
              disabled={scanning}
              className={cn(
                'px-4 py-1.5 text-xs flex items-center gap-2 rounded-lg transition-all font-mono',
                scanning
                  ? 'bg-cyan-500/10 text-cyan-400 cursor-wait'
                  : 'btn-cockpit-primary'
              )}
            >
              {scanning ? (
                <><m.div className="w-3 h-3 border-2 border-cyan-400 border-t-transparent rounded-full" animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} /> Scanning...</>
              ) : (
                <><RefreshCw size={12} /> Discover Providers</>
              )}
            </button>
            <button
              onClick={() => setMonitoring(!monitoring)}
              className={cn(
                'px-4 py-1.5 text-xs flex items-center gap-2 rounded-lg transition-all font-mono border',
                monitoring
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'border-jarvis-border/20 text-jarvis-text-dim hover:text-jarvis-cyan hover:border-jarvis-cyan/30'
              )}
            >
              <Activity size={12} />
              {monitoring ? 'Monitoring' : 'Start Monitor'}
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Provider Grid */}
        <div className="xl:col-span-2 space-y-3">
          <GlassPanel className="p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">
                Discovered Providers <span className="text-jarvis-text-dim/30">({MOCK_PROVIDERS.filter(p => p.available).length} available)</span>
              </span>
            </div>
            <div className="space-y-2">
              {MOCK_PROVIDERS.map((provider) => (
                <m.div
                  key={provider.name}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={cn(
                    'flex items-center justify-between p-3 rounded-lg border transition-all duration-200',
                    provider.available
                      ? 'border-jarvis-border/20 bg-jarvis-bg-2/20 hover:border-jarvis-border/40'
                      : 'border-jarvis-border/10 bg-jarvis-bg-2/10 opacity-50'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center',
                      provider.available ? 'bg-emerald-500/10' : 'bg-jarvis-bg-3'
                    )}>
                      <Server size={14} className={provider.available ? 'text-emerald-400' : 'text-jarvis-text-dim/30'} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-jarvis-text">{provider.name}</span>
                        {provider.free && <NeonBadge color="green">Free</NeonBadge>}
                      </div>
                      <div className="text-[10px] font-mono text-jarvis-text-dim/40 mt-0.5">
                        {provider.baseUrl}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div className="text-xs font-mono font-bold text-jarvis-text">{provider.score}</div>
                      <div className="text-[9px] font-mono text-jarvis-text-dim/40">Score</div>
                    </div>
                    {provider.available && (
                      <div className="text-right">
                        <div className="text-xs font-mono text-jarvis-text-dim/70">{provider.latency}ms</div>
                        <div className="text-[9px] font-mono text-jarvis-text-dim/40">Latency</div>
                      </div>
                    )}
                    <StatusDot status={provider.available ? 'active' : 'inactive'} />
                  </div>
                </m.div>
              ))}
            </div>
          </GlassPanel>
        </div>

        {/* Right Panel: Health & Stats */}
        <div className="xl:col-span-1 space-y-4">
          {/* Health Summary */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Health Summary</span>
            <div className="mt-3 space-y-3">
              {[
                { label: 'Available', value: '4/6', icon: CheckCircle2, color: 'text-emerald-400' },
                { label: 'Avg Latency', value: '213ms', icon: Zap, color: 'text-cyan-400' },
                { label: 'Free Tier', value: '3 providers', icon: Shield, color: 'text-amber-400' },
                { label: 'Best Score', value: '92', icon: Activity, color: 'text-violet-400' },
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

          {/* Capability Filter */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Capabilities</span>
            <div className="mt-3 flex flex-wrap gap-2">
              {['chat', 'code', 'vision', 'image', 'embeddings', 'audio'].map((cap) => (
                <span key={cap} className="px-2.5 py-1 rounded-md bg-jarvis-bg-2/50 border border-jarvis-border/20 text-[10px] font-mono text-jarvis-text-dim/60 hover:text-jarvis-cyan hover:border-jarvis-cyan/30 transition-all cursor-pointer">
                  {cap}
                </span>
              ))}
            </div>
          </GlassPanel>

          {/* Quick Score Guide */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Scoring</span>
            <div className="mt-3 space-y-2 text-[10px] font-mono text-jarvis-text-dim/50">
              <div className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-emerald-400/50" /> Latency: &lt;200ms = 30pts</div>
              <div className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-cyan-400/50" /> Free tier: +25pts bonus</div>
              <div className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-violet-400/50" /> Models: up to 20pts</div>
              <div className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-amber-400/50" /> Capabilities: +5pts each</div>
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
