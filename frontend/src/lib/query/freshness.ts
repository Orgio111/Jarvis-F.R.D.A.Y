/**
 * Freshness classes for React Query caching.
 *
 * The codebase had ad-hoc staleTime/refetchInterval values scattered per call
 * site (4s, 8s, 10s, 30s, 60s) with no shared policy. Centralising those
 * choices into a small set of named classes makes:
 *
 *   - cache TTL decisions explicit and reviewable
 *   - cross-query consistency easier to maintain
 *   - localStorage persistence filtering trivial (just key the persistence
 *     decision off the class).
 *
 * Usage:
 *
 *   useQuery({
 *     queryKey: queryKey('providers'),
 *     queryFn: () => apiClient.get('/providers'),
 *     ...freshness.slowlyChanging,
 *   });
 */

import type { UseQueryOptions } from '@tanstack/react-query';

type CachePolicy = Pick<UseQueryOptions, 'staleTime' | 'gcTime' | 'refetchInterval'>;

export const freshness = {
  /**
   * Configuration data that essentially never changes during a session.
   * FeatureFlags, system metadata, app version. Re-fetch is wasteful.
   */
  static: {
    staleTime: Infinity,
    gcTime: 24 * 60 * 60 * 1000, // 24h
  } satisfies CachePolicy,

  /**
   * Slowly-changing reference data: provider list, model catalog, settings.
   * Cache for 5 minutes; keep in memory for an hour so route switches reuse it.
   */
  slowlyChanging: {
    staleTime: 5 * 60 * 1000, // 5 min
    gcTime: 60 * 60 * 1000, // 1 h
  } satisfies CachePolicy,

  /**
   * Resource state: memory store, search index, tools list. Changes when the
   * user performs actions but doesn't drift on its own.
   */
  resourceState: {
    staleTime: 30 * 1000, // 30s
    gcTime: 15 * 60 * 1000, // 15 min
  } satisfies CachePolicy,

  /**
   * Live operational data: GPU utilization, system metrics. Polled.
   */
  live: {
    staleTime: 5 * 1000, // 5s
    gcTime: 5 * 60 * 1000, // 5 min
    refetchInterval: 10 * 1000, // 10s
  } satisfies CachePolicy,

  /**
   * High-frequency telemetry: monitoring dashboard. Polls aggressively.
   */
  realtime: {
    staleTime: 3 * 1000,
    gcTime: 2 * 60 * 1000,
    refetchInterval: 5 * 1000,
  } satisfies CachePolicy,
} as const;

export type FreshnessKey = keyof typeof freshness;

/**
 * The set of query-key prefixes whose data is safe to persist across page
 * reloads. Live/realtime queries are excluded because their data is stale
 * by the time the user reloads.
 */
export const PERSISTED_QUERY_KEYS: ReadonlySet<string> = new Set([
  'bootstrap',
  'providers',
  'models',
  'features',
  'settings',
  'search-status',
  'memory-status',
  'self-improvement-status',
  'local-actions',
  'tools',
]);
