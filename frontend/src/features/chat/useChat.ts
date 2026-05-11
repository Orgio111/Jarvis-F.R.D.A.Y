import { useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { apiUrl } from '@/lib/config/env';
import { getSessionId, generateRequestId } from '@/lib/session/session';
import { normalizeEvent } from '@/lib/realtime/eventNormalizer';
import type { BackendEvent } from '@/lib/api/types';
import type {
  ChatStreamStartPayload,
  ChatStreamTokenPayload,
  ChatStreamEndPayload,
  ChatStreamErrorPayload,
} from './chatTypes';
import { useChatStore } from './chatStore';

export function useChat() {
  const { addMessage, updateMessage, appendToken, setStreaming } = useChatStore();

  const sendMessage = useCallback(async (content: string, modelId?: string) => {
    if (!content.trim()) return;

    const userMsgId = `msg_${uuidv4()}`;
    const assistantMsgId = `msg_${uuidv4()}`;
    const now = new Date().toISOString();

    addMessage({
      id: userMsgId,
      role: 'user',
      content: content.trim(),
      status: 'complete',
      timestamp: now,
    });

    addMessage({
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      status: 'pending',
      timestamp: now,
    });

    setStreaming(true, assistantMsgId);

    const messages = useChatStore.getState().messages
      .filter((m) => m.status !== 'error')
      .map((m) => ({ role: m.role, content: m.content }));

    const body: Record<string, unknown> = {
      messages,
      stream: true,
    };
    if (modelId) body.model = modelId;

    try {
      const url = apiUrl('/chat/completions');
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': generateRequestId(),
          'X-Session-ID': getSessionId(),
          'X-Client-Version': import.meta.env.VITE_CLIENT_VERSION ?? '0.1.0',
        },
        body: JSON.stringify(body),
      });

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}`);
      }

      updateMessage(assistantMsgId, { status: 'streaming' });

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || trimmed === 'data: [DONE]') continue;

          const event = normalizeEvent(trimmed.replace(/^data:\s*/, '')) as BackendEvent | null;
          if (!event) continue;

          switch (event.type) {
            case 'CHAT_STREAM_START': {
              const p = event.payload as ChatStreamStartPayload;
              updateMessage(assistantMsgId, {
                modelId: p.model,
                providerId: p.providerId,
                status: 'streaming',
              });
              break;
            }
            case 'CHAT_STREAM_TOKEN': {
              const p = event.payload as ChatStreamTokenPayload;
              appendToken(assistantMsgId, p.token);
              break;
            }
            case 'CHAT_STREAM_END': {
              const p = event.payload as ChatStreamEndPayload;
              updateMessage(assistantMsgId, {
                content: p.content,
                status: 'complete',
                modelId: p.model,
                providerId: p.providerId,
              });
              setStreaming(false, null);
              break;
            }
            case 'CHAT_STREAM_ERROR': {
              const p = event.payload as ChatStreamErrorPayload;
              updateMessage(assistantMsgId, { status: 'error', error: p.error });
              setStreaming(false, null);
              break;
            }
          }
        }
      }

      // Ensure streaming flag is cleared even if END event was missed
      setStreaming(false, null);
      const current = useChatStore.getState().messages.find((m) => m.id === assistantMsgId);
      if (current?.status === 'streaming') {
        updateMessage(assistantMsgId, { status: 'complete' });
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      updateMessage(assistantMsgId, { status: 'error', error: msg });
      setStreaming(false, null);
    }
  }, [addMessage, updateMessage, appendToken, setStreaming]);

  return { sendMessage };
}
