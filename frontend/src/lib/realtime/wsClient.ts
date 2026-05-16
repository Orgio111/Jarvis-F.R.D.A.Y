/**
 * WebSocket client.
 * Connects to ws://localhost:8000/ws/* endpoints.
 * Reconnects with exponential backoff + jitter (avoids thundering-herd
 * reconnects after a server restart).
 * Detects silent connection drops via a "no message in N seconds" watchdog
 * and forces reconnect — covers cases where the TCP layer remains open but
 * the upstream stream has stalled.
 */

import { wsUrl } from '@/lib/config/env';
import { getSessionId, generateRequestId } from '@/lib/session/session';
import { normalizeEvent } from './eventNormalizer';
import type { BackendEvent } from '@/lib/api/types';

export type WSEventHandler<T = unknown> = (_event: BackendEvent<T>) => void;
export type WSRawHandler = (_data: string) => void;

interface WSClientOptions {
  path: string;
  onEvent?: WSEventHandler;
  onRaw?: WSRawHandler;
  onOpen?: () => void;
  onClose?: (_code: number, _reason: string) => void;
  onError?: (_err: Event) => void;
  maxReconnectDelay?: number;
  initialReconnectDelay?: number;
  autoReconnect?: boolean;
  /**
   * If no message is received in this many ms, the client considers the
   * connection stalled and forces a reconnect. Set to 0 to disable.
   * Default: 90_000 (matches server pong timeout * 1.5).
   */
  silenceTimeoutMs?: number;
}

export class WSClient {
  private ws: WebSocket | null = null;
  private reconnectDelay: number;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private silenceTimer: ReturnType<typeof setTimeout> | null = null;
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
      silenceTimeoutMs: 90_000,
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
      this.armSilenceWatchdog();
      this.opts.onOpen();
    };

    this.ws.onmessage = (e: MessageEvent) => {
      this.armSilenceWatchdog();
      const raw = typeof e.data === 'string' ? e.data : JSON.stringify(e.data);
      try {
        this.opts.onRaw(raw);
        const event = normalizeEvent(raw);
        if (event) this.opts.onEvent(event);
      } catch (err) {
        // Handler errors must not break the read pump.
        console.warn('[ws] handler error', err);
      }
    };

    this.ws.onclose = (e) => {
      this.clearSilenceWatchdog();
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

  /**
   * Resets the silence watchdog. Called on open and every received message.
   * If the watchdog fires, the underlying socket is force-closed which
   * triggers `onclose` → reconnect via the normal path.
   */
  private armSilenceWatchdog(): void {
    this.clearSilenceWatchdog();
    if (this.opts.silenceTimeoutMs <= 0) return;
    this.silenceTimer = setTimeout(() => {
      console.warn(`[ws] no data for ${this.opts.silenceTimeoutMs}ms, forcing reconnect`);
      try {
        this.ws?.close(4000, 'silence-timeout');
      } catch {
        /* ignore */
      }
    }, this.opts.silenceTimeoutMs);
  }

  private clearSilenceWatchdog(): void {
    if (this.silenceTimer) {
      clearTimeout(this.silenceTimer);
      this.silenceTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.stopped) return;
    // Full jitter: pick a random delay in [0, reconnectDelay]. Standard
    // approach to avoid thundering-herd reconnects after a server restart.
    const jittered = Math.floor(Math.random() * this.reconnectDelay);
    this.reconnectTimer = setTimeout(() => {
      if (!this.stopped) this.connect();
    }, jittered);
    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.opts.maxReconnectDelay);
  }

  close(code = 1000, reason = 'client closed'): void {
    this.stopped = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.clearSilenceWatchdog();
    this.ws?.close(code, reason);
    this.ws = null;
  }

  get readyState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }
}
