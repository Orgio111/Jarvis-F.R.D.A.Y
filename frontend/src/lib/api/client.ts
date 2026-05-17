/**
 * API client.
 *
 * - Automatically injects X-Request-ID, X-Session-ID, X-Client-Version headers.
 * - Parses canonical ApiSuccess / ApiErrorEnvelope responses.
 * - Throws ApiError on API-level errors, NetworkError on fetch failures.
 * - ONLY communicates with http://localhost:8000/api (enforced via env.apiBaseUrl).
 */

import { env, apiUrl } from '@/lib/config/env';
import { getSessionId, generateRequestId } from '@/lib/session/session';

import { ApiError, NetworkError } from './errors';

import type { ApiResponse, ApiSuccess } from './types';

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  /** Override the generated requestId (useful in tests). */
  requestId?: string;
  signal?: AbortSignal;
}

async function requestEnvelope<T>(path: string, options: RequestOptions = {}): Promise<ApiSuccess<T>> {
  const url = path.startsWith('http') ? path : apiUrl(path);
  const requestId = options.requestId ?? generateRequestId();
  const sessionId = getSessionId();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Request-ID': requestId,
    'X-Session-ID': sessionId,
    'X-Client-Version': env.clientVersion,
    ...options.headers,
  };

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      signal: options.signal,
    });
  } catch (err) {
    throw new NetworkError(err, url);
  }

  let json: ApiResponse<T>;
  try {
    json = (await response.json()) as ApiResponse<T>;
  } catch {
    throw new ApiError(
      'parse_error',
      `Failed to parse response from ${url}`,
      requestId,
      new Date().toISOString(),
      undefined,
      response.status,
    );
  }

  if (!json.ok) {
    throw ApiError.fromEnvelope(json, response.status);
  }

  return json;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const envelope = await requestEnvelope<T>(path, options);
  return envelope.data;
}

// ─── Convenience methods ───────────────────────────────────────────────────────

export const apiClient = {
  /** Access the full envelope (with correlationId/timestamp). */
  envelope: requestEnvelope,

  get: <T>(path: string, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'GET' }),

  post: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method'>) =>
    request<T>(path, { ...opts, method: 'POST', body }),

  patch: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method'>) =>
    request<T>(path, { ...opts, method: 'PATCH', body }),

  put: <T>(path: string, body?: unknown, opts?: Omit<RequestOptions, 'method'>) =>
    request<T>(path, { ...opts, method: 'PUT', body }),

  delete: <T>(path: string, opts?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...opts, method: 'DELETE' }),

  /** POST a FormData body (e.g. file uploads). Skips Content-Type so the browser sets multipart boundary. */
  postForm: async <T>(path: string, form: FormData): Promise<T> => {
    const url = path.startsWith('http') ? path : apiUrl(path);
    let response: Response;
    try {
      response = await fetch(url, {
        method: 'POST',
        headers: {
          'X-Request-ID': generateRequestId(),
          'X-Session-ID': getSessionId(),
          'X-Client-Version': env.clientVersion,
        },
        body: form,
      });
    } catch (err) {
      throw new NetworkError(err, url);
    }
    const json = (await response.json()) as { ok: boolean; data: T };
    if (!json.ok) throw new Error('Form upload failed');
    return json.data;
  },
};

export default apiClient;
