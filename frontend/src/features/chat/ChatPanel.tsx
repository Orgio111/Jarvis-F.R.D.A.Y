import { useEffect, useRef } from 'react';
import { m } from 'framer-motion';
import { MessageSquare, Trash2 } from 'lucide-react';
import { useChatStore } from './chatStore';
import { useChat } from './useChat';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { ModelSelector } from './ModelSelector';
import { GlassPanel } from '@/components/ui/GlassPanel';

export function ChatPanel() {
  const messages = useChatStore((s) => s.messages);
  const isStreaming = useChatStore((s) => s.isStreaming);
  const clearMessages = useChatStore((s) => s.clearMessages);
  const { sendMessage } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-jarvis-border/50 bg-jarvis-bg-2/50 backdrop-blur-sm shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-jarvis-cyan/10 flex items-center justify-center">
            <MessageSquare size={14} className="text-jarvis-cyan" />
          </div>
          <div>
            <span className="text-jarvis-cyan text-xs font-mono font-semibold tracking-wider">CHAT</span>
            {isStreaming && (
              <m.span
                className="text-jarvis-text-dim text-[10px] font-mono ml-2"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                — streaming
              </m.span>
            )}
          </div>
          {/* Model Mode Selector */}
          <ModelSelector disabled={isStreaming} />
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="flex items-center gap-1.5 text-jarvis-text-dim text-xs font-mono hover:text-jarvis-red transition-all duration-200 px-2 py-1 rounded hover:bg-jarvis-red/5"
          >
            <Trash2 size={12} />
            clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-1 scrollbar-thin">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          <m.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
          >
            {messages.map((msg, i) => (
              <m.div
                key={msg.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i === messages.length - 1 ? 0 : 0 }}
              >
                <MessageBubble message={msg} />
              </m.div>
            ))}
          </m.div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full gap-8 py-12">
      <m.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4 }}
      >
        <GlassPanel className="p-8 text-center max-w-sm" glow>
          {/* JARVIS avatar */}
          <m.div
            className="w-16 h-16 mx-auto mb-5 flex items-center justify-center rounded-2xl bg-gradient-to-br from-jarvis-cyan/20 to-jarvis-blue/10 border border-jarvis-cyan/30"
            animate={{ boxShadow: [
              '0 0 20px rgba(0,212,255,0.1)',
              '0 0 40px rgba(0,212,255,0.2)',
              '0 0 20px rgba(0,212,255,0.1)',
            ]}}
            transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
          >
            <span className="text-jarvis-cyan text-3xl font-bold neon-cyan">J</span>
          </m.div>
          <p className="text-jarvis-text-bright text-sm font-mono mb-1 tracking-wide">
            J.A.R.V.I.S. Online
          </p>
          <p className="text-jarvis-text-dim text-xs font-mono leading-relaxed">
            Ask me anything. I can reason, code, search, and remember.
          </p>
        </GlassPanel>
      </m.div>

      <m.div
        className="grid grid-cols-2 gap-2 w-full max-w-sm"
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.3 }}
      >
        {SUGGESTIONS.map((s, i) => (
          <m.div
            key={s}
            className="jarvis-panel px-3 py-2.5 text-xs font-mono text-jarvis-text-dim text-center rounded-xl cursor-default hover:text-jarvis-cyan hover:border-jarvis-cyan/30 transition-all duration-200"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + i * 0.1, duration: 0.3 }}
          >
            {s}
          </m.div>
        ))}
      </m.div>
    </div>
  );
}

const SUGGESTIONS = [
  'What can you do?',
  'Show GPU status',
  'Write a Python script',
  'Search the web',
];
