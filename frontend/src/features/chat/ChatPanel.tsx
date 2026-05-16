import { useEffect, useRef } from 'react';
import { useChatStore } from './chatStore';
import { useChat } from './useChat';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
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
      <div className="flex items-center justify-between px-4 py-2 border-b border-jarvis-border bg-jarvis-bg-2 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-jarvis-cyan text-xs font-mono font-semibold tracking-wider">CHAT</span>
          {isStreaming && (
            <span className="text-jarvis-text-dim text-xs font-mono animate-pulse">
              — streaming
            </span>
          )}
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="text-jarvis-text-dim text-xs font-mono hover:text-jarvis-red transition-colors"
          >
            clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map((msg) => <MessageBubble key={msg.id} message={msg} />)
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
    <div className="flex flex-col items-center justify-center h-full gap-6 py-12">
      <GlassPanel className="p-8 text-center max-w-sm">
        <div className="w-14 h-14 mx-auto mb-4 flex items-center justify-center rounded-full border border-jarvis-cyan">
          <span className="text-jarvis-cyan text-2xl font-bold">J</span>
        </div>
        <p className="text-jarvis-text-bright text-sm font-mono mb-1">
          JARVIS Online
        </p>
        <p className="text-jarvis-text-dim text-xs font-mono">
          Ask me anything. I can reason, code, search, and remember.
        </p>
      </GlassPanel>
      <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
        {SUGGESTIONS.map((s) => (
          <p key={s} className="jarvis-panel px-3 py-2 text-xs font-mono text-jarvis-text-dim text-center rounded cursor-default hover:text-jarvis-cyan hover:border-jarvis-cyan/30 transition-colors">
            {s}
          </p>
        ))}
      </div>
    </div>
  );
}

const SUGGESTIONS = [
  'What can you do?',
  'Show GPU status',
  'Write a Python script',
  'Search the web',
];
