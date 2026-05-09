import { describe, it, expect } from 'vitest';
import { normalizeEvent } from '@/lib/realtime/eventNormalizer';
import type { BackendEvent } from '@/lib/api/types';

describe('eventNormalizer', () => {
  it('parses a valid BackendEvent', () => {
    const raw: BackendEvent = {
      id: 'evt_123',
      type: 'chat.token',
      version: '1.0',
      timestamp: new Date().toISOString(),
      correlationId: 'corr_123',
      requestId: 'req_456',
      sessionId: 'sess_789',
      source: 'backend',
      payload: { token: 'Hello' },
    };
    const result = normalizeEvent(JSON.stringify(raw));
    expect(result).not.toBeNull();
    expect(result?.type).toBe('chat.token');
    expect(result?.id).toBe('evt_123');
  });

  it('returns null for empty string', () => {
    expect(normalizeEvent('')).toBeNull();
  });

  it('returns null for SSE comment lines', () => {
    expect(normalizeEvent(': heartbeat')).toBeNull();
  });

  it('returns null for malformed JSON', () => {
    expect(normalizeEvent('{bad json')).toBeNull();
  });

  it('returns null for JSON without required fields', () => {
    expect(normalizeEvent(JSON.stringify({ ok: true }))).toBeNull();
  });
});
