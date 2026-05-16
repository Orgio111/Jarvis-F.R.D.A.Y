package config

import (
	"os"
	"strconv"
	"strings"
)

// Config holds all gateway configuration loaded from environment variables.
type Config struct {
	AppEnv  string
	AppName string
	AppHost string
	AppPort string

	PythonAIServiceURL string
	RustBrokerURL      string
	RedisURL           string

	CORSAllowedOrigins []string
	RateLimitPerMinute int

	PrometheusEnabled bool
	OTELEnabled       bool
	OTELServiceName   string
	OTELSampleRate    float64
	JaegerEndpoint    string

	GPUEnabled         bool
	GPURequired        bool
	GPUAllowCPUFallback bool

	LocalLLMEnabled bool
}

func Load() *Config {
	return &Config{
		AppEnv:  getEnv("APP_ENV", "development"),
		AppName: getEnv("APP_NAME", "jarvis-backend"),
		AppHost: getEnv("APP_HOST", "0.0.0.0"),
		AppPort: getEnv("APP_PORT", "8000"),

		PythonAIServiceURL: getEnv("PYTHON_AI_SERVICE_URL", "http://localhost:8100"),
		RustBrokerURL:      getEnv("RUST_BROKER_URL", "http://localhost:8200"),
		RedisURL:           getEnv("REDIS_URL", "redis://localhost:6379/0"),

		CORSAllowedOrigins: splitEnv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,tauri://localhost"),
		RateLimitPerMinute: getEnvInt("REQUEST_RATE_LIMIT_PER_MINUTE", 120),

		PrometheusEnabled: getEnvBool("PROMETHEUS_ENABLED", true),
		OTELEnabled:       getEnvBool("OTEL_ENABLED", true),
		OTELServiceName:   getEnv("OTEL_SERVICE_NAME", "jarvis-gateway"),
		OTELSampleRate:    getEnvFloat("OTEL_TRACES_SAMPLE_RATE", 1.0),
		JaegerEndpoint:    getEnv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces"),

		GPUEnabled:          getEnvBool("GPU_ENABLED", true),
		GPURequired:         getEnvBool("GPU_REQUIRED", false),
		GPUAllowCPUFallback: getEnvBool("GPU_ALLOW_CPU_FALLBACK", true),

		LocalLLMEnabled: getEnvBool("LOCAL_LLM_ENABLED", false),
	}
}

func getEnv(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func getEnvBool(key string, fallback bool) bool {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	b, err := strconv.ParseBool(v)
	if err != nil {
		return fallback
	}
	return b
}

func getEnvFloat(key string, fallback float64) float64 {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	f, err := strconv.ParseFloat(v, 64)
	if err != nil {
		return fallback
	}
	return f
}

func getEnvInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	i, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return i
}

func splitEnv(key, fallback string) []string {
	v := getEnv(key, fallback)
	parts := strings.Split(v, ",")
	result := make([]string, 0, len(parts))
	for _, p := range parts {
		if t := strings.TrimSpace(p); t != "" {
			result = append(result, t)
		}
	}
	return result
}
