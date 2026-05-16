import { m } from 'framer-motion';
import type { ChatMessage } from './chatTypes';

interface Props {
  message: ChatMessage;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const isError = message.status === 'error';

  return (
    <m.div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      {!isUser && (
        <div className="w-6 h-6 rounded-full border border-jarvis-cyan flex items-center justify-center mr-2 mt-1 shrink-0">
          <span className="text-jarvis-cyan text-xs font-bold">J</span>
        </div>
      )}

      <div
        className={[
          'max-w-[75%] rounded-lg px-4 py-3 text-sm font-mono leading-relaxed',
          isUser
            ? 'bg-jarvis-cyan/10 border border-jarvis-cyan/30 text-jarvis-text-bright'
            : isError
              ? 'bg-jarvis-red/10 border border-jarvis-red/30 text-jarvis-red'
              : 'bg-jarvis-bg-2 border border-jarvis-border text-jarvis-text-bright',
        ].join(' ')}
      >
        {isError ? (
          <span className="text-jarvis-red">
            ⚠ {message.error ?? 'An error occurred.'}
          </span>
        ) : (
          <>
            <span className="whitespace-pre-wrap break-words">{message.content}</span>
            {message.status === 'streaming' && (
              <span className="inline-block w-1.5 h-4 ml-0.5 bg-jarvis-cyan animate-pulse" />
            )}
            {message.status === 'pending' && (
              <span className="text-jarvis-text-dim text-xs ml-1">thinking…</span>
            )}
          </>
        )}

        {message.modelId && message.status === 'complete' && (
          <div className="mt-1.5 text-jarvis-text-dim text-xs opacity-60">
            {message.modelId}
          </div>
        )}
      </div>
    </m.div>
  );
}
