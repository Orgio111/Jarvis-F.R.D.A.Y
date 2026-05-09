/**
 * Frontend environment config.
 * All values come from VITE_ prefixed variables only.
 * NO provider secrets. NO internal service URLs.
 */

function requireEnv(key: string, fallback?: string): string {
  const value = import.meta.env[key] as string | undefined;
  if (value !== undefined && value !== '') return value;
  if (fallback !== undefined) return fallback;
  console.warn(`[env] ${key} not set; using empty string`);
  return '';
}

export const env = {
  /** Public REST API base: http://localhost:8000/api */
  apiBaseUrl: requireEnv('VITE_API_BASE_URL', 'http://localhost:8000/api'),

  /** Public WebSocket base: ws://localhost:8000/ws */
  wsBaseUrl: requireEnv('VITE_WS_BASE_URL', 'ws://localhost:8000/ws'),

  appVersion: requireEnv('VITE_APP_VERSION', '0.1.0'),
  clientVersion: requireEnv('VITE_CLIENT_VERSION', '0.1.0'),

  enableGpuUi: requireEnv('VITE_ENABLE_GPU_UI', 'true') === 'true',
  enableWebglVisuals: requireEnv('VITE_ENABLE_WEBGL_VISUALS', 'true') === 'true',
  enableWebgpuVisuals: requireEnv('VITE_ENABLE_WEBGPU_VISUALS', 'true') === 'true',
  enablePerformanceMode: requireEnv('VITE_ENABLE_PERFORMANCE_MODE', 'true') === 'true',

  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const;

/** Constructs a full REST URL from a path segment. */
export function apiUrl(path: string): string {
  const base = env.apiBaseUrl.replace(/\/$/, '');
  return `${base}/${path.replace(/^\//, '')}`;
}

/** Constructs a full WebSocket URL from a path segment. */
export function wsUrl(path: string): string {
  const base = env.wsBaseUrl.replace(/\/$/, '');
  return `${base}/${path.replace(/^\//, '')}`;
}

/** Constructs an SSE URL from a feature path. */
export function sseUrl(path: string): string {
  return apiUrl(path);
}
