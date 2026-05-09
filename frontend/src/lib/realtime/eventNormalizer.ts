import type { BackendEvent } from '@/lib/api/types';

/**
 * Parses raw SSE / WebSocket data into a typed BackendEvent envelope.
 * Returns null for malformed or non-event data (heartbeat comments, etc.).
 */
export function normalizeEvent<T = unknown>(rawData: string): BackendEvent<T> | null {
  if (!rawData || rawData.trim() === '' || rawData.startsWith(':')) {
    return null;
  }

  try {
    const parsed = JSON.parse(rawData) as BackendEvent<T>;

    if (!parsed || typeof parsed !== 'object') return null;
    if (!parsed.type || !parsed.id) return null;

    return {
      id: parsed.id,
      type: parsed.type,
      version: parsed.version ?? '1.0',
      timestamp: parsed.timestamp ?? new Date().toISOString(),
      correlationId: parsed.correlationId ?? '',
      requestId: parsed.requestId ?? null,
      sessionId: parsed.sessionId ?? null,
      source: parsed.source ?? 'backend',
      payload: parsed.payload,
    };
  } catch {
    return null;
  }
}
