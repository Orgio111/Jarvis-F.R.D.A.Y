import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { Monitor, Globe, MousePointer2, Type, Camera, Play, StopCircle, History, Maximize2 } from 'lucide-react';
import { GlassPanel } from '@/components/ui/GlassPanel';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusDot } from '@/components/ui/StatusDot';
import { NeonBadge } from '@/components/ui/NeonBadge';
import { cn } from '@/lib/utils';

interface BrowserTab {
  id: string;
  title: string;
  url: string;
  active: boolean;
}

export function DeviceAgentPanel() {
  const [connected, setConnected] = useState(false);
  const [url, setUrl] = useState('');
  const [tabs] = useState<BrowserTab[]>([
    { id: 't1', title: 'JARVIS Dashboard', url: 'http://localhost:8000', active: true },
  ]);
  const [actionLog, setActionLog] = useState<string[]>([
    '[14:23:01] Agent initialized',
    '[14:23:05] Navigated to http://localhost:8000',
    '[14:23:08] Analyzing page structure...',
    '[14:23:12] Found 24 interactive elements',
    '[14:23:15] Waiting for instruction...',
  ]);

  return (
    <div className="h-full flex flex-col gap-4 p-4">
      <SectionHeader
        title="Device Agent"
        subtitle="Desktop & browser automation"
        icon={Monitor}
        actions={
          <button
            onClick={() => setConnected(!connected)}
            className={cn(
              'px-4 py-1.5 text-xs flex items-center gap-2 rounded-lg transition-all duration-200 font-mono',
              connected
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                : 'bg-jarvis-bg-3 text-jarvis-text-dim border border-jarvis-border/20 hover:text-jarvis-cyan hover:border-jarvis-cyan/30'
            )}
          >
            <StatusDot status={connected ? 'active' : 'inactive'} />
            {connected ? 'Connected' : 'Connect Agent'}
          </button>
        }
      />

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 flex-1 min-h-0">
        {/* Browser Viewport */}
        <div className="xl:col-span-2">
          <GlassPanel className="h-full flex flex-col">
            {/* Browser Toolbar */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-jarvis-border/20">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500/50" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500/50" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/50" />
              </div>
              <div className="flex-1 flex items-center gap-2 mx-2">
                <div className="flex-1 flex items-center gap-2 px-3 py-1 rounded-md bg-jarvis-bg-2/50 border border-jarvis-border/20">
                  <Globe size={12} className="text-jarvis-text-dim/40 shrink-0" />
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="Enter URL..."
                    className="flex-1 bg-transparent text-xs font-mono text-jarvis-text placeholder:text-jarvis-text-dim/20 outline-none"
                  />
                </div>
                <button className="btn-cockpit-primary px-3 py-1 text-xs flex items-center gap-1.5">
                  <Play size={12} /> Go
                </button>
              </div>
              <button className="p-1.5 rounded text-jarvis-text-dim/40 hover:text-jarvis-cyan hover:bg-jarvis-cyan/5 transition-all">
                <Maximize2 size={14} />
              </button>
            </div>

            {/* Browser Content */}
            <div className="flex-1 relative overflow-hidden bg-gradient-to-br from-jarvis-bg via-jarvis-bg-2/50 to-jarvis-bg">
              {connected ? (
                <div className="absolute inset-4 rounded-xl border border-jarvis-border/20 bg-jarvis-bg-2/30 flex items-center justify-center">
                  <div className="text-center">
                    <Monitor size={48} className="mx-auto text-jarvis-cyan/30 mb-3" />
                    <p className="text-xs font-mono text-jarvis-text-dim/60">Browser viewport active</p>
                    <p className="text-[10px] font-mono text-jarvis-text-dim/30 mt-1">1280 × 720 · Chromium</p>
                  </div>
                </div>
              ) : (
                <div className="absolute inset-4 rounded-xl border-2 border-dashed border-jarvis-border/10 flex items-center justify-center">
                  <div className="text-center">
                    <Monitor size={40} className="mx-auto text-jarvis-text-dim/20 mb-3" />
                    <p className="text-xs font-mono text-jarvis-text-dim/30">Agent disconnected</p>
                    <p className="text-[10px] font-mono text-jarvis-text-dim/20 mt-1">Click Connect to start browser automation</p>
                  </div>
                </div>
              )}
            </div>
          </GlassPanel>
        </div>

        {/* Controls & Logs */}
        <div className="xl:col-span-1 space-y-3">
          {/* Action Controls */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Actions</span>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {[
                { icon: MousePointer2, label: 'Click', desc: 'Click element' },
                { icon: Type, label: 'Type', desc: 'Type text' },
                { icon: Camera, label: 'Screenshot', desc: 'Capture screen' },
                { icon: History, label: 'Analyze UI', desc: 'Scan elements' },
              ].map((action) => (
                <m.button
                  key={action.label}
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="flex flex-col items-center gap-1.5 p-3 rounded-lg border border-jarvis-border/20 bg-jarvis-bg-2/30 hover:border-jarvis-cyan/30 hover:bg-jarvis-cyan/5 transition-all duration-200"
                >
                  <action.icon size={16} className="text-jarvis-text-dim/60 group-hover:text-jarvis-cyan" />
                  <span className="text-[10px] font-mono text-jarvis-text-dim/60">{action.label}</span>
                </m.button>
              ))}
            </div>
          </GlassPanel>

          {/* Action Log */}
          <GlassPanel className="flex-1 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">Action Log</span>
              <button className="text-[10px] font-mono text-jarvis-text-dim/30 hover:text-jarvis-cyan">Clear</button>
            </div>
            <div className="space-y-1">
              {actionLog.map((entry, i) => (
                <m.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="text-[10px] font-mono text-jarvis-text-dim/50 leading-relaxed"
                >
                  {entry}
                </m.div>
              ))}
            </div>
          </GlassPanel>

          {/* Open Tabs */}
          <GlassPanel className="p-4">
            <span className="text-[10px] font-mono text-jarvis-text-dim/60 uppercase tracking-[0.15em]">
              Open Pages <span className="text-jarvis-text-dim/30">({tabs.length})</span>
            </span>
            <div className="mt-2 space-y-1">
              {tabs.map((tab) => (
                <div key={tab.id} className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-jarvis-bg-2/30 text-xs font-mono text-jarvis-text-dim/60">
                  <Globe size={10} className="shrink-0" />
                  <span className="truncate">{tab.title}</span>
                </div>
              ))}
            </div>
          </GlassPanel>
        </div>
      </div>
    </div>
  );
}
