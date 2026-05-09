import type { ApiErrorEnvelope } from './types';

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly correlationId: string,
    public readonly timestamp: string,
    public readonly details?: Record<string, unknown>,
    public readonly httpStatus?: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }

  static fromEnvelope(envelope: ApiErrorEnvelope, httpStatus?: number): ApiError {
    return new ApiError(
      envelope.error.code,
      envelope.error.message,
      envelope.correlationId,
      envelope.timestamp,
      envelope.error.details,
      httpStatus,
    );
  }

  get isProviderUnavailable(): boolean {
    return this.code === 'provider_unavailable';
  }

  get isServiceUnavailable(): boolean {
    return this.code === 'service_unavailable';
  }

  get isRateLimited(): boolean {
    return this.code === 'rate_limit_exceeded';
  }

  get isNotFound(): boolean {
    return this.code === 'not_found';
  }

  get isAuthError(): boolean {
    return this.code === 'missing_session_id' || this.code === 'missing_client_version';
  }
}

export class NetworkError extends Error {
  constructor(
    public readonly cause: unknown,
    public readonly url: string,
  ) {
    super(`Network error reaching ${url}`);
    this.name = 'NetworkError';
  }
}

export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError;
}

export function isNetworkError(err: unknown): err is NetworkError {
  return err instanceof NetworkError;
}

export function getErrorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  if (err instanceof NetworkError) return `Cannot reach the JARVIS backend. Is it running?`;
  if (err instanceof Error) return err.message;
  return 'An unknown error occurred';
}
