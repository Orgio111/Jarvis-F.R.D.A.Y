package handlers

import (
	"context"
	"encoding/json"
	"net/http"
	"time"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	mw "github.com/orgio111/jarvis/go-gateway/internal/http/middleware"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
	"github.com/orgio111/jarvis/go-gateway/pkg/version"
)

// BootstrapHandler handles GET /api/bootstrap
type BootstrapHandler struct {
	cfg     *config.Config
	aiProxy *proxy.AIProxy
	startedAt time.Time
}

// NewBootstrapHandler creates a BootstrapHandler.
func NewBootstrapHandler(cfg *config.Config, aiProxy *proxy.AIProxy) *BootstrapHandler {
	return &BootstrapHandler{
		cfg:       cfg,
		aiProxy:   aiProxy,
		startedAt: time.Now(),
	}
}

// ServeHTTP handles the bootstrap request.
// It proxies to Python AI service for full bootstrap data.
// If Python is unavailable, returns a safe default bootstrap with degraded status.
func (h *BootstrapHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	correlationID := mw.GetCorrelationID(r)
	ctx := r.Context()

	bootstrapData, err := h.fetchFromPython(ctx, correlationID)
	if err != nil {
		// Python unavailable — return safe default bootstrap
		bootstrapData = contracts.DefaultBootstrapData(
			h.cfg.AppName,
			h.cfg.AppEnv,
			version.Version,
			h.cfg.GPURequired,
		)
		bootstrapData.System.Uptime = formatUptime(time.Since(h.startedAt))
	} else {
		bootstrapData.System.Uptime = formatUptime(time.Since(h.startedAt))
	}

	contracts.WriteSuccess(w, correlationID, bootstrapData)
}

func (h *BootstrapHandler) fetchFromPython(ctx context.Context, correlationID string) (contracts.BootstrapData, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	result, err := h.aiProxy.Get(ctx, "/bootstrap", correlationID, "")
	if err != nil {
		return contracts.BootstrapData{}, err
	}

	if !result.IsOK() {
		return contracts.BootstrapData{}, errServiceError("python-ai-service")
	}

	// Python returns a wrapped envelope; unwrap it.
	var envelope struct {
		Ok   bool                  `json:"ok"`
		Data contracts.BootstrapData `json:"data"`
	}
	if err := json.Unmarshal(result.Body, &envelope); err != nil {
		return contracts.BootstrapData{}, err
	}
	return envelope.Data, nil
}

func formatUptime(d time.Duration) string {
	d = d.Round(time.Second)
	h := int(d.Hours())
	m := int(d.Minutes()) % 60
	s := int(d.Seconds()) % 60
	if h > 0 {
		return formatDuration(h, "h", m, "m", s, "s")
	}
	if m > 0 {
		return formatDuration(m, "m", s, "s", 0, "")
	}
	return formatDuration(s, "s", 0, "", 0, "")
}

func formatDuration(v1 int, u1 string, v2 int, u2 string, v3 int, u3 string) string {
	s := ""
	if v1 > 0 {
		s += intToStr(v1) + u1
	}
	if v2 > 0 {
		s += intToStr(v2) + u2
	}
	if v3 > 0 && u3 != "" {
		s += intToStr(v3) + u3
	}
	return s
}

func intToStr(n int) string {
	if n < 10 {
		return "0" + string(rune('0'+n))
	}
	return string(rune('0'+n/10)) + string(rune('0'+n%10))
}

type serviceError struct{ service string }

func (e *serviceError) Error() string { return e.service + " returned error" }
func errServiceError(svc string) error { return &serviceError{service: svc} }
