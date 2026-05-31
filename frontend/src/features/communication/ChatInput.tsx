import React, { useRef, useState, useCallback } from 'react';
import { Send, Sparkles } from 'lucide-react';

interface Props {
  onSend: (_content: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled = false }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 180) + 'px';
  };

  return (
    <div className="flex items-end gap-2.5 p-4 border-t border-jarvis-border/50 bg-jarvis-bg-2/50 backdrop-blur-sm">
      <div className="flex-1 relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
          <Sparkles size={14} className="text-jarvis-text-dim/30" />
        </div>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={disabled ? 'Waiting for response…' : 'Message JARVIS…'}
          rows={1}
          className={[
            'w-full resize-none rounded-xl border bg-jarvis-bg/80',
            'pl-9 pr-4 py-2.5 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim/40',
            'focus:outline-none focus:border-jarvis-cyan/40 focus:ring-1 focus:ring-jarvis-cyan/15',
            'transition-all duration-200 max-h-[180px] overflow-y-auto',
            disabled ? 'opacity-50 cursor-not-allowed' : '',
            'border-jarvis-border/30 hover:border-jarvis-border/60',
          ].join(' ')}
        />
      </div>
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className={[
          'flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-mono font-medium',
          'transition-all duration-200 shrink-0',
          disabled || !value.trim()
            ? 'opacity-40 cursor-not-allowed bg-jarvis-cyan/5 text-jarvis-text-dim border border-jarvis-border/20'
            : 'bg-jarvis-cyan text-jarvis-bg border border-jarvis-cyan hover:shadow-[0_0_20px_rgba(0,212,255,0.4)] hover:brightness-110 active:scale-[0.98]',
        ].join(' ')}
      >
        <Send size={14} />
        Send
      </button>
    </div>
  );
}
