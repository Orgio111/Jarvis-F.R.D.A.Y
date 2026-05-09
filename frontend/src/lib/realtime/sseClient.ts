/**
 * SSE client.
 * Connects to /api/* stream endpoints.
 * Reconnects automatically with exponential backoff.
 * Dispatches normalised BackendEvent objects to registered handlers.
 */

import { env } from '@/lib/config/env';
import { getSessionId, generateRequestId } from '@/lib/session/session';
import { normalizeEvent } from './eventNormalizer';
import type { BackendEvent } from '@/lib/api/types';

export type SSEEventHandler<T = unknown> = (event: BackendEvent<T>) => void;
export type SSEErrorHandler = (err: Event | Error) => void;

interface SSEClientOptions {
  url: string;
  onEvent: SSEEventHandler;
  onError?: SSEErrorHandler;
  onOpen?: () => void;
  onClose?: () => void;
  maxReconnectDelay?: number;
  initialReconnectDelay?: number;
}

export class SSEClient {
  private es: EventSource | null = null;
  private reconnectDelay: number;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private readonly options: Required<SSEClientOptions>;

  constructor(options: SSEClientOptions) {
    this.options = {
      onError: () => {},
      onOpen: () => {},
      onClose: () => {},
      maxReconnectDelay: 30_000,
      initialReconnectDelay: 1_000,
      ...options,
    };
    this.reconnectDelay = this.options.initialReconnectDelay;
    this.connect();
  }

  private buildUrl(): string {
    const url = new URL(this.options.url, window.location.href);
    url.searchParams.set('sessionId', getSessionId());
    url.searchParams.set('requestId', generateRequestId());
    return url.toString();
  }

  private connect(): void {
    if (this.stopped) return;

    const fullUrl = this.buildUrl();
    this.es = new EventSource(fullUrl);

    this.es.onopen = () => {
      this.reconnectDelay = this.options.initialReconnectDelay;
      this.options.onOpen();
    };

    this.es.onmessage = (e: MessageEvent) => {
      const event = normalizeEvent(e.data);
      if (event) this.options.onEvent(event);
    };

    // Named event listeners (Go gateway sends "event: <type>" lines)
    this.es.addEventListener('message', (e: MessageEvent) => {
      const event = normalizeEvent(e.data);
      if (event) this.options.onEvent(event);
    });

    this.es.onerror = (e) => {
      this.options.onError(e);
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    if (this.stopped) return;
    this.es?.close();
    this.es = null;
    this.options.onClose();

    this.reconnectTimer = setTimeout(() => {
      if (!this.stopped) this.connect();
    }, this.reconnectDelay);

    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.options.maxReconnectDelay);
  }

  close(): void {
    this.stopped = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.es?.close();
    this.es = null;
    this.options.onClose();
  }
}

/** Creates a one-time-use SSE client as a React cleanup-friendly hook helper. */
export function connectSSE(
  path: string,
  onEvent: SSEEventHandler,
  onError?: SSEErrorHandler,
): () => void {
  const url = path.startsWith('http') ? path : `${env.apiBaseUrl}/${path.replace(/^\//, '')}`;
  const client = new SSEClient({ url, onEvent, onError });
  return () => client.close();
}
