/**
 * WebSocket client.
 * Connects to ws://localhost:8000/ws/* endpoints.
 * Reconnects with exponential backoff.
 * Normalises incoming messages to BackendEvent envelopes.
 */

import { env, wsUrl } from '@/lib/config/env';
import { getSessionId, generateRequestId } from '@/lib/session/session';
import { normalizeEvent } from './eventNormalizer';
import type { BackendEvent } from '@/lib/api/types';

export type WSEventHandler<T = unknown> = (event: BackendEvent<T>) => void;
export type WSRawHandler = (data: string) => void;

interface WSClientOptions {
  path: string;
  onEvent?: WSEventHandler;
  onRaw?: WSRawHandler;
  onOpen?: () => void;
  onClose?: (code: number, reason: string) => void;
  onError?: (err: Event) => void;
  maxReconnectDelay?: number;
  initialReconnectDelay?: number;
  autoReconnect?: boolean;
}

export class WSClient {
  private ws: WebSocket | null = null;
  private reconnectDelay: number;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private readonly opts: Required<WSClientOptions>;

  constructor(options: WSClientOptions) {
    this.opts = {
      onEvent: () => {},
      onRaw: () => {},
      onOpen: () => {},
      onClose: () => {},
      onError: () => {},
      maxReconnectDelay: 30_000,
      initialReconnectDelay: 1_000,
      autoReconnect: true,
      ...options,
    };
    this.reconnectDelay = this.opts.initialReconnectDelay;
    this.connect();
  }

  private buildUrl(): string {
    const base = wsUrl(this.opts.path);
    const sep = base.includes('?') ? '&' : '?';
    return `${base}${sep}sessionId=${getSessionId()}&requestId=${generateRequestId()}`;
  }

  private connect(): void {
    if (this.stopped) return;

    this.ws = new WebSocket(this.buildUrl());

    this.ws.onopen = () => {
      this.reconnectDelay = this.opts.initialReconnectDelay;
      this.opts.onOpen();
    };

    this.ws.onmessage = (e: MessageEvent) => {
      const raw = typeof e.data === 'string' ? e.data : JSON.stringify(e.data);
      this.opts.onRaw(raw);
      const event = normalizeEvent(raw);
      if (event) this.opts.onEvent(event);
    };

    this.ws.onclose = (e) => {
      this.opts.onClose(e.code, e.reason);
      if (this.opts.autoReconnect && !this.stopped) this.scheduleReconnect();
    };

    this.ws.onerror = (e) => {
      this.opts.onError(e);
    };
  }

  send(data: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private scheduleReconnect(): void {
    if (this.stopped) return;
    this.reconnectTimer = setTimeout(() => {
      if (!this.stopped) this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.opts.maxReconnectDelay);
  }

  close(code = 1000, reason = 'client closed'): void {
    this.stopped = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close(code, reason);
    this.ws = null;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}
