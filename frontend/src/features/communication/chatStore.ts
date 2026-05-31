import { create } from 'zustand';
import type { ChatMessage, ChatMode, ModeAvailabilityItem } from './chatTypes';

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamingMessageId: string | null;

  // ── Model mode system ────────────────────────────────────────────────────────
  selectedMode: ChatMode;
  manualModelId: string;          // empty = auto (use mode resolution)
  availableModes: ModeAvailabilityItem[];
  isModesLoading: boolean;

  addMessage: (_msg: ChatMessage) => void;
  updateMessage: (_id: string, _patch: Partial<ChatMessage>) => void;
  appendToken: (_id: string, _token: string) => void;
  setStreaming: (_streaming: boolean, _messageId: string | null) => void;
  setSelectedMode: (_mode: ChatMode) => void;
  setManualModelId: (_modelId: string) => void;
  setAvailableModes: (_modes: ModeAvailabilityItem[], _loading: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  streamingMessageId: null,

  selectedMode: 'fast',
  manualModelId: '',
  availableModes: [],
  isModesLoading: true,

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

  setSelectedMode: (mode) => set({ selectedMode: mode }),

  setManualModelId: (modelId) => set({ manualModelId: modelId }),

  setAvailableModes: (modes, loading) =>
    set({ availableModes: modes, isModesLoading: loading }),

  clearMessages: () => set({ messages: [], isStreaming: false, streamingMessageId: null }),
}));
