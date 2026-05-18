package proxy

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/sony/gobreaker"
	"go.opentelemetry.io/contrib/instrumentation/net/http/otelhttp"
)

// ErrCircuitOpen is returned when the circuit breaker trips.
var ErrCircuitOpen = errors.New("ai service circuit open — too many recent failures")

// AIProxy is the HTTP client used to communicate with the Python AI service.
type AIProxy struct {
	baseURL    string
	httpClient *http.Client
	cb         *gobreaker.CircuitBreaker
}

// New creates a new AIProxy pointing at the given base URL.
func New(baseURL string, timeout time.Duration) *AIProxy {
	base := &http.Transport{
		MaxIdleConns:        100,
		MaxIdleConnsPerHost: 20,
		IdleConnTimeout:     90 * time.Second,
	}

	cb := gobreaker.NewCircuitBreaker(gobreaker.Settings{
		Name:        "ai-service",
		MaxRequests: 5,                // half-open: max simultaneous probes
		Interval:    60 * time.Second, // rolling window
		Timeout:     30 * time.Second, // open → half-open wait
		ReadyToTrip: func(counts gobreaker.Counts) bool {
			// Trip when ≥5 consecutive failures or failure ratio > 60 %
			if counts.ConsecutiveFailures >= 5 {
				return true
			}
			if counts.Requests > 0 {
				ratio := float64(counts.TotalFailures) / float64(counts.Requests)
				return counts.Requests >= 10 && ratio >= 0.6
			}
			return false
		},
	})

	return &AIProxy{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout:   timeout,
			Transport: otelhttp.NewTransport(base),
		},
		cb: cb,
	}
}

// ProxyResult holds the decoded JSON body and HTTP status from the AI service.
type ProxyResult struct {
	StatusCode int
	Body       json.RawMessage
}

// CircuitState returns the current breaker state as a string.
func (p *AIProxy) CircuitState() string {
	return p.cb.State().String()
}

// Get issues a GET request to the Python AI service and returns the raw JSON body.
func (p *AIProxy) Get(ctx context.Context, path string, correlationID, sessionID string) (*ProxyResult, error) {
	return p.do(ctx, http.MethodGet, path, nil, correlationID, sessionID)
}

// Post issues a POST request to the Python AI service.
func (p *AIProxy) Post(ctx context.Context, path string, body any, correlationID, sessionID string) (*ProxyResult, error) {
	return p.do(ctx, http.MethodPost, path, body, correlationID, sessionID)
}

// Patch issues a PATCH request to the Python AI service.
func (p *AIProxy) Patch(ctx context.Context, path string, body any, correlationID, sessionID string) (*ProxyResult, error) {
	return p.do(ctx, http.MethodPatch, path, body, correlationID, sessionID)
}

func (p *AIProxy) do(ctx context.Context, method, path string, body any, correlationID, sessionID string) (*ProxyResult, error) {
	url := p.baseURL + path

	var reqBody io.Reader
	if body != nil {
		data, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("marshal request body: %w", err)
		}
		reqBody = newBytesReader(data)
	}

	// Wrap the actual HTTP call inside the circuit breaker.
	result, err := p.cb.Execute(func() (any, error) {
		req, err := http.NewRequestWithContext(ctx, method, url, reqBody)
		if err != nil {
			return nil, fmt.Errorf("create request: %w", err)
		}

		req.Header.Set("Content-Type", "application/json")
		req.Header.Set("X-Correlation-ID", correlationID)
		if sessionID != "" {
			req.Header.Set("X-Session-ID", sessionID)
		}
		req.Header.Set("X-Source", "go-gateway")

		resp, err := p.httpClient.Do(req)
		if err != nil {
			return nil, fmt.Errorf("ai service request: %w", err)
		}
		defer resp.Body.Close()

		raw, err := io.ReadAll(resp.Body)
		if err != nil {
			return nil, fmt.Errorf("read response body: %w", err)
		}

		// Treat 5xx as circuit-breaking failures.
		if resp.StatusCode >= 500 {
			return nil, fmt.Errorf("ai service returned %d", resp.StatusCode)
		}

		return &ProxyResult{
			StatusCode: resp.StatusCode,
			Body:       json.RawMessage(raw),
		}, nil
	})

	if err != nil {
		if errors.Is(err, gobreaker.ErrOpenState) || errors.Is(err, gobreaker.ErrTooManyRequests) {
			return nil, ErrCircuitOpen
		}
		return nil, err
	}

	return result.(*ProxyResult), nil
}

// DecodeInto unmarshals the proxy result body into v.
func (r *ProxyResult) DecodeInto(v any) error {
	return json.Unmarshal(r.Body, v)
}

// IsOK returns true if the HTTP status is 2xx.
func (r *ProxyResult) IsOK() bool {
	return r.StatusCode >= 200 && r.StatusCode < 300
}

// bytesReader wraps a []byte to implement io.Reader.
type bytesReader struct {
	data   []byte
	offset int
}

func newBytesReader(b []byte) *bytesReader {
	return &bytesReader{data: b}
}

func (br *bytesReader) Read(p []byte) (int, error) {
	if br.offset >= len(br.data) {
		return 0, io.EOF
	}
	n := copy(p, br.data[br.offset:])
	br.offset += n
	return n, nil
}
