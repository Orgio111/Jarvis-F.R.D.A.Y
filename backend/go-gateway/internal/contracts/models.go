package contracts

// Model DTOs used across model endpoints.

type Model struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	ProviderID   string   `json:"providerId"`
	ProviderName string   `json:"providerName"`
	Groups       []string `json:"groups"`
	ContextWindow int     `json:"contextWindow"`
	MaxTokens    int      `json:"maxTokens"`
	SupportsVision bool   `json:"supportsVision"`
	SupportsTools  bool   `json:"supportsTools"`
	DeviceMode   string   `json:"deviceMode"` // "cloud" | "gpu" | "cpu" | "disabled"
	IsDefault    bool     `json:"isDefault"`
	IsFree       bool     `json:"isFree"`
	Description  string   `json:"description,omitempty"`
}

type ModelGroup struct {
	ID     string  `json:"id"`
	Label  string  `json:"label"`
	Models []Model `json:"models"`
}

type ModelSelectRequest struct {
	ModelID  string `json:"modelId"`
	UseCase  string `json:"useCase,omitempty"` // "chat" | "coding" | "embedding" | etc.
}

type ModelSelectResponse struct {
	Selected Model  `json:"selected"`
	Reason   string `json:"reason"`
}

type ModelDefaults struct {
	Chat      string `json:"chat"`
	Coder     string `json:"coder"`
	Fast      string `json:"fast"`
	Embedding string `json:"embedding"`
	Vision    string `json:"vision"`
	STT       string `json:"stt"`
	TTS       string `json:"tts"`
}

type OrchestrationRequest struct {
	Models  []string `json:"models"`
	Prompt  string   `json:"prompt"`
	Mode    string   `json:"mode"` // "debate" | "review" | "consensus"
}

type OrchestrationJob struct {
	JobID     string `json:"jobId"`
	Status    string `json:"status"` // "pending" | "running" | "completed" | "error"
	StreamURL string `json:"streamUrl"`
}
