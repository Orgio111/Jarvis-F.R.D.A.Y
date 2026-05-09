package contracts

// Chat DTOs

type ChatMessage struct {
	Role    string `json:"role"` // "user" | "assistant" | "system" | "tool"
	Content string `json:"content"`
}

type ChatSendRequest struct {
	SessionID string        `json:"sessionId"`
	Messages  []ChatMessage `json:"messages"`
	ModelID   string        `json:"modelId,omitempty"`
	Stream    bool          `json:"stream"`
	MaxTokens *int          `json:"maxTokens,omitempty"`
	SystemPrompt string     `json:"systemPrompt,omitempty"`
}

// ChatSendResponse is returned immediately after POST /api/chat/send.
// The actual content arrives via SSE at StreamURL.
type ChatSendResponse struct {
	RequestID      string `json:"requestId"`
	SessionID      string `json:"sessionId"`
	Status         string `json:"status"` // "streaming"
	StreamURL      string `json:"streamUrl"`
	WebSocketTopic string `json:"websocketTopic"`
}

type ChatSession struct {
	SessionID   string        `json:"sessionId"`
	Title       string        `json:"title"`
	MessageCount int          `json:"messageCount"`
	CreatedAt   string        `json:"createdAt"`
	UpdatedAt   string        `json:"updatedAt"`
	ModelID     string        `json:"modelId"`
	Messages    []ChatMessage `json:"messages,omitempty"`
}

type UsageSummary struct {
	PromptTokens     int    `json:"promptTokens"`
	CompletionTokens int    `json:"completionTokens"`
	TotalTokens      int    `json:"totalTokens"`
	ProviderID       string `json:"providerId"`
	ModelID          string `json:"modelId"`
	LatencyMs        int    `json:"latencyMs"`
}
