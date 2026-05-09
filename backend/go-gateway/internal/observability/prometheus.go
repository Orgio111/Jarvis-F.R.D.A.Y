package observability

import (
	"net/http"
	"strconv"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	httpRequestsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "jarvis",
			Subsystem: "gateway",
			Name:      "http_requests_total",
			Help:      "Total number of HTTP requests handled by the gateway.",
		},
		[]string{"method", "path", "status"},
	)

	httpRequestDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Namespace: "jarvis",
			Subsystem: "gateway",
			Name:      "http_request_duration_seconds",
			Help:      "HTTP request latency distribution.",
			Buckets:   prometheus.DefBuckets,
		},
		[]string{"method", "path", "status"},
	)

	activeSSEConnections = promauto.NewGauge(prometheus.GaugeOpts{
		Namespace: "jarvis",
		Subsystem: "gateway",
		Name:      "sse_connections_active",
		Help:      "Number of currently open SSE connections.",
	})

	activeWSConnections = promauto.NewGauge(prometheus.GaugeOpts{
		Namespace: "jarvis",
		Subsystem: "gateway",
		Name:      "ws_connections_active",
		Help:      "Number of currently open WebSocket connections.",
	})

	proxyErrorsTotal = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Namespace: "jarvis",
			Subsystem: "gateway",
			Name:      "proxy_errors_total",
			Help:      "Total proxy errors when calling downstream services.",
		},
		[]string{"service"},
	)
)

// MetricsHandler returns the Prometheus metrics HTTP handler.
func MetricsHandler() http.Handler {
	return promhttp.Handler()
}

// Instrument wraps a handler to record Prometheus metrics.
func Instrument(path string, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rw := &statusRecorder{ResponseWriter: w, status: 200}
		next.ServeHTTP(rw, r)

		dur := time.Since(start).Seconds()
		status := strconv.Itoa(rw.status)

		httpRequestsTotal.WithLabelValues(r.Method, path, status).Inc()
		httpRequestDuration.WithLabelValues(r.Method, path, status).Observe(dur)
	})
}

func IncSSEConnections()  { activeSSEConnections.Inc() }
func DecSSEConnections()  { activeSSEConnections.Dec() }
func IncWSConnections()   { activeWSConnections.Inc() }
func DecWSConnections()   { activeWSConnections.Dec() }
func IncProxyError(svc string) { proxyErrorsTotal.WithLabelValues(svc).Inc() }

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (sr *statusRecorder) WriteHeader(status int) {
	sr.status = status
	sr.ResponseWriter.WriteHeader(status)
}
