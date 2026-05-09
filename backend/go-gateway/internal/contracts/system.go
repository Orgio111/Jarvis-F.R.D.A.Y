package contracts

// System status DTOs

type SystemStatus struct {
	Status     string              `json:"status"` // "healthy" | "degraded" | "down"
	Version    string              `json:"version"`
	AppEnv     string              `json:"appEnv"`
	Uptime     string              `json:"uptime"`
	StartedAt  string              `json:"startedAt"`
	Components map[string]CompStatus `json:"components"`
}

type CompStatus struct {
	Name    string `json:"name"`
	Status  string `json:"status"` // "ok" | "degraded" | "down"
	Message string `json:"message,omitempty"`
	Latency *int   `json:"latencyMs,omitempty"`
}

type SystemMetrics struct {
	Timestamp    string  `json:"timestamp"`
	CPUPercent   float64 `json:"cpuPercent"`
	MemPercent   float64 `json:"memPercent"`
	MemUsedMB    int64   `json:"memUsedMb"`
	MemTotalMB   int64   `json:"memTotalMb"`
	DiskPercent  float64 `json:"diskPercent"`
	RequestRate  float64 `json:"requestsPerSecond"`
	ErrorRate    float64 `json:"errorsPerSecond"`
	P99LatencyMs float64 `json:"p99LatencyMs"`
}

type HealthResponse struct {
	Status    string              `json:"status"`
	Version   string              `json:"version"`
	Timestamp string              `json:"timestamp"`
	Checks    map[string]HealthCheck `json:"checks"`
}

type HealthCheck struct {
	Status  string `json:"status"` // "pass" | "warn" | "fail"
	Message string `json:"message,omitempty"`
}
