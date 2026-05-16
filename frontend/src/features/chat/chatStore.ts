import { create } from 'zustand';
import type { ChatMessage } from './chatTypes';

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;
  selectedModel: string;
  addMessage: (_msg: ChatMessage) => void;
  updateMessage: (_id: string, _patch: Partial<ChatMessage>) => void;
  appendToken: (_id: string, _token: string) => void;
  setStreaming: (_streaming: boolean, _messageId: string | null) => void;
  setSelectedModel: (_model: string) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  streamingMessageId: null,
  selectedModel: '',

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  updateMessage: (id, patch) =>
    set((s) => ({
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
    })),

  appendToken: (id, token) =>
    set((s) => ({
      messages: s.messages.map((m) =>
        m.id === id ? { ...m, content: m.content + token } : m,
      ),
    })),

  setStreaming: (streaming, messageId) =>
    set({ isStreaming: streaming, streamingMessageId: messageId }),

  setSelectedModel: (model) => set({ selectedModel: model }),

  clearMessages: () => set({ messages: [], isStreaming: false, streamingMessageId: null }),
}));
