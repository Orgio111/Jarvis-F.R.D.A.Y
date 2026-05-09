/**
 * Canonical event type constants — matches Go/Python backend.
 */

export const EventTypes = {
  PROVIDER_ROUTING_DECISION:    'provider.routing.decision',
  MODEL_SELECTED:               'model.selected',
  GPU_WORKLOAD_ASSIGNED:        'gpu.workload.assigned',
  CHAT_STARTED:                 'chat.started',
  CHAT_TOKEN:                   'chat.token',
  CHAT_COMPLETED:               'chat.completed',
  USAGE_SUMMARY:                'usage.summary',
  PROVIDER_FALLBACK_STARTED:    'provider.fallback.started',
  PROVIDER_FALLBACK_COMPLETED:  'provider.fallback.completed',
  GPU_STATUS_CHANGED:           'gpu.status.changed',
  GPU_METRICS_UPDATE:           'gpu.metrics.update',
  SYSTEM_STATUS:                'system.status',
  PROVIDER_STATUS:              'provider.status',
  LOCAL_ACTION_PENDING:         'local.action.pending',
  LOCAL_ACTION_APPROVED:        'local.action.approved',
  LOCAL_ACTION_REJECTED:        'local.action.rejected',
  SELF_IMPROVEMENT_PROPOSAL:    'self.improvement.proposal',
  MEMORY_SYNTHESIS_COMPLETE:    'memory.synthesis.complete',
  EXECUTION_STARTED:            'execution.started',
  EXECUTION_COMPLETED:          'execution.completed',
  EXECUTION_FAILED:             'execution.failed',
  LOG_LINE:                     'log.line',
  HEARTBEAT:                    'heartbeat',
  DONE:                         'done',
} as const;

export type EventType = (typeof EventTypes)[keyof typeof EventTypes];
