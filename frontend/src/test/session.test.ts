import { describe, it, expect, beforeEach } from 'vitest';
import { getSessionId, generateRequestId, resetSession } from '@/lib/session/session';

describe('session', () => {
  beforeEach(() => {
    resetSession();
  });

  it('returns a session ID prefixed with sess_', () => {
    const id = getSessionId();
    expect(id.startsWith('sess_')).toBe(true);
  });

  it('returns the same session ID on repeated calls', () => {
    const id1 = getSessionId();
    const id2 = getSessionId();
    expect(id1).toBe(id2);
  });

  it('generates unique request IDs', () => {
    const id1 = generateRequestId();
    const id2 = generateRequestId();
    expect(id1.startsWith('req_')).toBe(true);
    expect(id1).not.toBe(id2);
  });

  it('resets session on resetSession()', () => {
    const id1 = getSessionId();
    resetSession();
    const id2 = getSessionId();
    expect(id1).not.toBe(id2);
  });
});
