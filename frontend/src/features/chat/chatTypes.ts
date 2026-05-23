export type MessageRole = 'user' | 'assistant' | 'system';
export type MessageStatus = 'pending' | 'streaming' | 'complete' | 'error';

// ─── Model Modes ────────────────────────────────────────────────────────────────

export type ChatMode = 'fast' | 'smart' | 'deep' | 'coding';

export const ALL_MODES: ChatMode[] = ['fast', 'smart', 'deep', 'coding'];

export const MODE_LABELS: Record<ChatMode, string> = {
  fast: 'FAST',
  smart: 'SMART',
  deep: 'DEEP',
  coding: 'CODING',
};

export const MODE_DESCRIPTIONS: Record<ChatMode, string> = {
  fast: 'Low-latency — Mixtral 8x22B',
  smart: 'Reasoning pro — DeepSeek-V4-Flash',
  deep: 'Max reasoning — DeepSeek-V4-Pro',
  coding: 'Code-optimised — Qwen-3-Coder 480B',
};

export const MODE_COLORS: Record<ChatMode, string> = {
  fast: 'text-jarvis-cyan',
  smart: 'text-jarvis-blue',
  deep: 'text-jarvis-purple',
  coding: 'text-jarvis-green',
};

export const MODE_BG_COLORS: Record<ChatMode, string> = {
  fast: 'bg-jarvis-cyan/10 border-jarvis-cyan/30',
  smart: 'bg-jarvis-blue/10 border-jarvis-blue/30',
  deep: 'bg-jarvis-purple/10 border-jarvis-purple/30',
  coding: 'bg-jarvis-green/10 border-jarvis-green/30',
};

export const MODE_HOVER_COLORS: Record<ChatMode, string> = {
  fast: 'hover:bg-jarvis-cyan/15 hover:border-jarvis-cyan/50',
  smart: 'hover:bg-jarvis-blue/15 hover:border-jarvis-blue/50',
  deep: 'hover:bg-jarvis-purple/15 hover:border-jarvis-purple/50',
  coding: 'hover:bg-jarvis-green/15 hover:border-jarvis-green/50',
};

export interface ModeResolvedModel {
  modelId: string;
  providerId: string;
  providerName: string;
  modelName: string;
}

export interface ModeAvailabilityItem {
  mode: ChatMode;
  displayName: string;
  description: string;
  resolved: ModeResolvedModel | null;
  availableModels: Array<{
    id: string;
    name: string;
    providerId: string;
    providerName: string;
    groups: string[];
    isFree: boolean;
  }>;
}

export interface ModelModesResponse {
  modes: ModeAvailabilityItem[];
}

// ─── Chat Message Types ─────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  timestamp: string;
  modelId?: string;
  providerId?: string;
  mode?: ChatMode;
  error?: string;
}

export interface ChatStreamStartPayload {
  messageId: string;
  model: string;
  providerId: string;
}

export interface ChatStreamTokenPayload {
  messageId: string;
  token: string;
}

export interface ChatStreamEndPayload {
  messageId: string;
  content: string;
  model: string;
  providerId: string;
}

export interface ChatStreamErrorPayload {
  messageId: string;
  error: string;
}
