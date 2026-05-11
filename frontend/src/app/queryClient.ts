import { QueryClient } from '@tanstack/react-query';
import { createSyncStoragePersister } from '@tanstack/query-sync-storage-persister';
import { persistQueryClient } from '@tanstack/react-query-persist-client';
import { env } from '@/lib/config/env';
import { PERSISTED_QUERY_KEYS } from '@/lib/query/freshness';

/**
 * Cache policy:
 *
 *   - `staleTime: 10s` baseline so brief route switches reuse data, but
 *     individual call sites should opt into a `freshness.*` policy that
 *     matches their data's churn rate. See lib/query/freshness.ts.
 *
 *   - `gcTime: 30min` keeps cold data around long enough to survive a route
 *     change or tab switch, but drops it before it gets truly stale.
 *
 *   - `refetchOnWindowFocus: false` because the polling queries are explicit
 *     `refetchInterval` users; auto-refetch on focus would double-trigger.
 *
 *   - `retry: 2` covers transient transport blips. Mutations don't retry —
 *     users should see the error and decide.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 10_000,
      gcTime: 30 * 60 * 1000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});

/**
 * Persist a subset of queries to localStorage so a page reload doesn't blank
 * the UI while bootstrap re-runs. Only "slowly-changing" data is persisted;
 * live polls (GPU, monitoring) are skipped because their data is stale by the
 * time the user reloads.
 *
 * The buster key includes the client version so a deploy automatically
 * invalidates any old cached payloads — prevents shape mismatches between
 * the frontend and a newly deployed API contract.
 */
if (typeof window !== 'undefined' && window.localStorage) {
  const persister = createSyncStoragePersister({
    storage: window.localStorage,
    key: 'jarvis-query-cache',
    throttleTime: 1000,
  });

  persistQueryClient({
    queryClient,
    persister,
    maxAge: 24 * 60 * 60 * 1000, // 24h
    buster: `jarvis-${env.clientVersion}`,
    dehydrateOptions: {
      shouldDehydrateQuery: (query) => {
        const firstKey = query.queryKey[0];
        if (typeof firstKey !== 'string') return false;
        return PERSISTED_QUERY_KEYS.has(firstKey);
      },
    },
  });
}
