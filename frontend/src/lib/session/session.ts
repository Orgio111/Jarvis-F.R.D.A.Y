/**
 * Session management.
 * The session ID is generated once per browser session and persisted in sessionStorage.
 * It is sent on every request as X-Session-ID.
 */

const SESSION_KEY = 'jarvis_session_id';

function generateSessionId(): string {
  return 'sess_' + crypto.randomUUID();
}

let _sessionId: string | null = null;

export function getSessionId(): string {
  if (_sessionId) return _sessionId;

  try {
    const stored = sessionStorage.getItem(SESSION_KEY);
    if (stored) {
      _sessionId = stored;
      return _sessionId;
    }
  } catch {
    // sessionStorage not available (e.g. in tests)
  }

  const newId = generateSessionId();
  _sessionId = newId;

  try {
    sessionStorage.setItem(SESSION_KEY, newId);
  } catch {
    // Ignore write errors
  }

  return _sessionId;
}

/** Generate a new request-scoped ID (UUID v4 with prefix). */
export function generateRequestId(): string {
  return 'req_' + crypto.randomUUID();
}

/** Reset the session (used for testing or explicit logout). */
export function resetSession(): void {
  _sessionId = null;
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // Ignore
  }
}
