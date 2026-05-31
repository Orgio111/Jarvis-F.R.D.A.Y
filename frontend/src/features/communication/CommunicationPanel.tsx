import { useState } from 'react';
import { m, AnimatePresence } from 'framer-motion';
import { MessageSquare, Mic } from 'lucide-react';
import { ChatPanel } from './ChatPanel';
import { VoicePanel } from './VoicePanel';
import { cn } from '@/lib/utils';

type Tab = 'chat' | 'voice';

const TABS: { key: Tab; label: string; icon: typeof MessageSquare }[] = [
  { key: 'chat', label: 'Chat', icon: MessageSquare },
  { key: 'voice', label: 'Voice', icon: Mic },
];

export function CommunicationPanel() {
  const [tab, setTab] = useState<Tab>('chat');

  return (
    <div className="flex flex-col h-full">
      {/* ── Tab bar ── */}
      <div className="jarvis-panel-header shrink-0">
        <div className="flex items-center gap-1">
          {TABS.map((t) => {
            const Icon = t.icon;
            const isActive = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 text-xs font-mono font-semibold tracking-wider rounded-lg transition-all duration-200',
                  isActive
                    ? 'bg-jarvis-cyan/10 text-jarvis-cyan border border-jarvis-cyan/30 shadow-[0_0_12px_rgba(0,212,255,0.15)]'
                    : 'text-jarvis-text-dim/50 hover:text-jarvis-text-dim/80 hover:bg-jarvis-bg-2/50 border border-transparent',
                )}
              >
                <Icon size={14} />
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Tab content ── */}
      <div className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          <m.div
            key={tab}
            initial={{ opacity: 0, x: tab === 'chat' ? -12 : 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: tab === 'chat' ? 12 : -12 }}
            transition={{ duration: 0.18, ease: 'easeOut' }}
            className="h-full"
          >
            {tab === 'chat' ? <ChatPanel /> : <VoicePanel />}
          </m.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
