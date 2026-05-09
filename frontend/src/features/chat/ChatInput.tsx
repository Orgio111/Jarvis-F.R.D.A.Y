import React, { useRef, useState, useCallback } from 'react';

interface Props {
  onSend: (content: string) => void;
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
    // Auto-grow textarea
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 180) + 'px';
  };

  return (
    <div className="flex items-end gap-2 p-3 border-t border-jarvis-border bg-jarvis-bg-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={disabled ? 'Waiting for response…' : 'Message JARVIS… (Enter to send, Shift+Enter for newline)'}
        rows={1}
        className={[
          'flex-1 resize-none rounded bg-jarvis-bg border border-jarvis-border',
          'px-3 py-2 text-sm font-mono text-jarvis-text-bright placeholder-jarvis-text-dim',
          'focus:outline-none focus:border-jarvis-cyan/60 focus:ring-1 focus:ring-jarvis-cyan/20',
          'transition-colors duration-150 max-h-[180px] overflow-y-auto',
          disabled ? 'opacity-50 cursor-not-allowed' : '',
        ].join(' ')}
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className={[
          'btn-cockpit-primary px-4 py-2 text-sm shrink-0 self-end',
          disabled || !value.trim() ? 'opacity-40 cursor-not-allowed' : '',
        ].join(' ')}
      >
        Send
      </button>
    </div>
  );
}
