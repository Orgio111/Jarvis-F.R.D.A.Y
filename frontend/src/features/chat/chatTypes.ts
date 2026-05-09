export type MessageRole = 'user' | 'assistant' | 'system';
export type MessageStatus = 'pending' | 'streaming' | 'complete' | 'error';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  status: MessageStatus;
  timestamp: string;
  modelId?: string;
  providerId?: string;
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
