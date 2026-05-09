package contracts

// Provider DTOs used across provider endpoints.

type Provider struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	BaseURL     string   `json:"baseUrl"`
	Status      string   `json:"status"` // "available" | "provider_unavailable" | "error" | "checking"
	Reason      string   `json:"reason,omitempty"`
	DeviceMode  string   `json:"deviceMode"` // "cloud" | "gpu" | "cpu" | "disabled"
	ModelCount  int      `json:"modelCount"`
	Capabilities []string `json:"capabilities"`
	IsDefault   bool     `json:"isDefault"`
	IsFallback  bool     `json:"isFallback"`
	Latency     *int     `json:"latencyMs,omitempty"`
}

type ProvidersHealthResponse struct {
	Overall   string     `json:"overall"` // "healthy" | "degraded" | "down"
	Providers []Provider `json:"providers"`
	CheckedAt string     `json:"checkedAt"`
}

type ProviderRoutingConfig struct {
	Mode        string `json:"mode"`    // "auto" | "primary" | "fallback"
	Primary     string `json:"primary"`
	Fallback    string `json:"fallback"`
	TimeoutSecs int    `json:"timeoutSeconds"`
	MaxRetries  int    `json:"maxRetries"`
}

type ProviderSwitchRequest struct {
	ProviderID string `json:"providerId"`
}

type ProviderMetrics struct {
	ProviderID     string  `json:"providerId"`
	RequestCount   int64   `json:"requestCount"`
	ErrorCount     int64   `json:"errorCount"`
	AvgLatencyMs   float64 `json:"avgLatencyMs"`
	TokensIn       int64   `json:"tokensIn"`
	TokensOut      int64   `json:"tokensOut"`
	FallbackCount  int64   `json:"fallbackCount"`
	Since          string  `json:"since"`
}
