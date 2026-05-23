import { m } from 'framer-motion';
import { Bot, User, AlertCircle, Zap, Brain, Sigma, Code2 } from 'lucide-react';
import type { ChatMessage } from './chatTypes';
import { MODE_LABELS, MODE_COLORS, MODE_BG_COLORS } from './chatTypes';

interface Props {
  message: ChatMessage;
}

const MODE_BADGE_ICONS: Record<string, typeof Zap> = {
  fast: Zap,
  smart: Brain,
  deep: Sigma,
  coding: Code2,
};

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const isError = message.status === 'error';
  const mode = message.mode;
  const ModeIcon = mode ? MODE_BADGE_ICONS[mode] : null;

  return (
    <m.div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
    >
      {/* JARVIS avatar */}
      {!isUser && (
        <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-jarvis-cyan/20 to-jarvis-blue/10 border border-jarvis-cyan/30 flex items-center justify-center mr-3 mt-0.5 shrink-0">
          <Bot size={14} className="text-jarvis-cyan" />
        </div>
      )}

      <div
        className={[
          'max-w-[75%] rounded-2xl px-4 py-3 text-sm font-mono leading-relaxed',
          'transition-all duration-200',
          isUser
            ? 'bg-jarvis-cyan/10 border border-jarvis-cyan/25 text-jarvis-text-bright rounded-tr-md'
            : isError
              ? 'bg-jarvis-red/10 border border-jarvis-red/25 text-jarvis-red rounded-tl-md'
              : 'bg-jarvis-bg-2/80 border border-jarvis-border/40 text-jarvis-text-bright rounded-tl-md',
        ].join(' ')}
      >
        {isError ? (
          <div className="flex items-start gap-2">
            <AlertCircle size={14} className="mt-0.5 shrink-0 text-jarvis-red" />
            <span>{message.error ?? 'An error occurred.'}</span>
          </div>
        ) : (
          <>
            <span className="whitespace-pre-wrap break-words">{message.content}</span>
            {message.status === 'streaming' && (
              <span className="inline-block w-1.5 h-4 ml-0.5 bg-jarvis-cyan animate-pulse rounded-sm" />
            )}
            {message.status === 'pending' && (
              <span className="inline-flex items-center gap-1.5 text-jarvis-text-dim text-xs ml-1">
                <span className="w-1 h-1 rounded-full bg-jarvis-cyan animate-pulse" />
                <span className="w-1 h-1 rounded-full bg-jarvis-cyan animate-pulse" style={{ animationDelay: '0.2s' }} />
                <span className="w-1 h-1 rounded-full bg-jarvis-cyan animate-pulse" style={{ animationDelay: '0.4s' }} />
              </span>
            )}
          </>
        )}

        {/* Footer: model info + mode badge */}
        {message.status === 'complete' && (message.modelId || mode) && (
          <div className="mt-2 pt-2 border-t border-jarvis-border/20 flex items-center gap-2 flex-wrap">
            {/* Mode badge */}
            {mode && ModeIcon && (
              <span
                className={[
                  'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-semibold',
                  'border',
                  MODE_BG_COLORS[mode],
                  MODE_COLORS[mode],
                ].join(' ')}
              >
                <ModeIcon size={8} />
                {MODE_LABELS[mode]}
              </span>
            )}
            {/* Model ID */}
            {message.modelId && (
              <span className="text-jarvis-text-dim text-[10px] opacity-50 font-mono truncate">
                {message.modelId}
              </span>
            )}
          </div>
        )}
      </div>

      {/* User avatar */}
      {isUser && (
        <div className="w-7 h-7 rounded-xl bg-jarvis-cyan/10 border border-jarvis-cyan/25 flex items-center justify-center ml-3 mt-0.5 shrink-0">
          <User size={14} className="text-jarvis-cyan/70" />
        </div>
      )}
    </m.div>
  );
}
