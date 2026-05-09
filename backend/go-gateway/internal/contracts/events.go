package contracts

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
)

// Event type constants — shared across Go gateway and frontend.
const (
	EventProviderRoutingDecision  = "provider.routing.decision"
	EventModelSelected            = "model.selected"
	EventGPUWorkloadAssigned      = "gpu.workload.assigned"
	EventChatStarted              = "chat.started"
	EventChatToken                = "chat.token"
	EventChatCompleted            = "chat.completed"
	EventUsageSummary             = "usage.summary"
	EventProviderFallbackStarted  = "provider.fallback.started"
	EventProviderFallbackCompleted = "provider.fallback.completed"
	EventGPUStatusChanged         = "gpu.status.changed"
	EventGPUMetricsUpdate         = "gpu.metrics.update"
	EventSystemStatus             = "system.status"
	EventProviderStatus           = "provider.status"
	EventLocalActionPending       = "local.action.pending"
	EventLocalActionApproved      = "local.action.approved"
	EventLocalActionRejected      = "local.action.rejected"
	EventSelfImprovementProposal  = "self.improvement.proposal"
	EventMemorySynthesisComplete  = "memory.synthesis.complete"
	EventExecutionStarted         = "execution.started"
	EventExecutionCompleted       = "execution.completed"
	EventExecutionFailed          = "execution.failed"
	EventLogLine                  = "log.line"
	EventHeartbeat                = "heartbeat"
)

// NewBackendEvent constructs a canonical event envelope.
func NewBackendEvent(eventType string, correlationID string, requestID, sessionID *string, payload any) BackendEvent {
	raw, _ := json.Marshal(payload)
	return BackendEvent{
		ID:            fmt.Sprintf("evt_%s", uuid.New().String()),
		Type:          eventType,
		Version:       "1.0",
		Timestamp:     time.Now().UTC().Format(time.RFC3339Nano),
		CorrelationID: correlationID,
		RequestID:     requestID,
		SessionID:     sessionID,
		Source:        "backend",
		Payload:       json.RawMessage(raw),
	}
}

// HeartbeatPayload is the payload for heartbeat events.
type HeartbeatPayload struct {
	IntervalSeconds int    `json:"intervalSeconds"`
	ServerTime      string `json:"serverTime"`
}
