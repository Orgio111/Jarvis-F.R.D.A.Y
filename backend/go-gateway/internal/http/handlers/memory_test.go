package handlers_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/orgio111/jarvis/go-gateway/internal/config"
	"github.com/orgio111/jarvis/go-gateway/internal/http/handlers"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// ─── shared test helpers (removed from old search_test.go/local_actions_test.go) ─

func newTestProxy(t *testing.T, handler http.Handler) (*proxy.AIProxy, string) {
	t.Helper()
	srv := httptest.NewServer(handler)
	t.Cleanup(srv.Close)
	return proxy.New(srv.URL, 5*time.Second), srv.URL
}

func newTestConfig(pythonURL string) *config.Config {
	return &config.Config{PythonAIServiceURL: pythonURL}
}

func decodeEnvelope(t *testing.T, body []byte) map[string]interface{} {
	t.Helper()
	var out map[string]interface{}
	if err := json.Unmarshal(body, &out); err != nil {
		t.Fatalf("cannot decode envelope: %v\nbody: %s", err, body)
	}
	return out
}

func okEnvelope(data interface{}) []byte {
	type env struct {
		Ok   bool        `json:"ok"`
		Data interface{} `json:"data"`
	}
	b, _ := json.Marshal(env{Ok: true, Data: data})
	return b
}

// ─── MemoryHandler ────────────────────────────────────────────────────────────

func TestMemoryStatus_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/memory/status", nil)
	rec := httptest.NewRecorder()
	h.Status(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 fallback, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	data, ok := env["data"].(map[string]interface{})
	if !ok {
		t.Fatalf("data is not an object: %T", env["data"])
	}
	if data["enabled"] != false {
		t.Errorf("expected enabled=false fallback, got %v", data["enabled"])
	}
}

func TestMemoryStatus_ServiceUp(t *testing.T) {
	payload := map[string]interface{}{"enabled": true, "faissAvailable": true}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/memory/status", nil)
	rec := httptest.NewRecorder()
	h.Status(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestMemorySearch_InvalidBody(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/memory/search",
		strings.NewReader(`not-json`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Search(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400 for invalid JSON, got %d", rec.Code)
	}
}

func TestMemorySearch_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/memory/search",
		strings.NewReader(`{"query":"test"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Search(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 fallback, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	data, ok := env["data"].(map[string]interface{})
	if !ok {
		t.Fatalf("data is not an object: %T", env["data"])
	}
	if data["total"] != 0.0 {
		t.Errorf("expected total=0 fallback, got %v", data["total"])
	}
}

func TestMemorySearch_Success(t *testing.T) {
	payload := map[string]interface{}{"results": []interface{}{}, "total": 0.0}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/memory/search",
		strings.NewReader(`{"query":"test"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Search(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestMemoryStore_InvalidBody(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/memory/store",
		strings.NewReader(`not-json`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Store(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400 for invalid JSON, got %d", rec.Code)
	}
}

func TestMemoryStore_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/memory/store",
		strings.NewReader(`{"key":"test","value":"data"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Store(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != false {
		t.Errorf("expected ok=false, got %v", env["ok"])
	}
}

func TestMemoryStore_Success(t *testing.T) {
	payload := map[string]interface{}{"stored": true}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/memory/store",
		strings.NewReader(`{"key":"test","value":"data"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Store(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestMemoryClear_Success(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	h := handlers.NewMemoryHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodDelete, "/api/memory/clear", nil)
	rec := httptest.NewRecorder()
	h.Clear(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	data, ok := env["data"].(map[string]interface{})
	if !ok {
		t.Fatalf("data is not an object: %T", env["data"])
	}
	if data["cleared"] != true {
		t.Errorf("expected cleared=true, got %v", data["cleared"])
	}
}

// ─── SearchHandler (merged from search.go → memory.go) ────────────────────────

func TestSearchStatus_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewSearchHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/search/status", nil)
	rec := httptest.NewRecorder()
	h.Status(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 fallback, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != true {
		t.Errorf("expected ok=true fallback, got %v", env["ok"])
	}
}

func TestSearchStatus_ServiceUp(t *testing.T) {
	data := map[string]interface{}{"enabled": true, "engine": "duckduckgo"}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(data))
	}))
	h := handlers.NewSearchHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/search/status", nil)
	rec := httptest.NewRecorder()
	h.Status(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestSearch_MissingQuery(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	h := handlers.NewSearchHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/search",
		strings.NewReader(`{}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Search(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestSearch_InvalidBody(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	h := handlers.NewSearchHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/search",
		strings.NewReader(`not-json`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Search(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400, got %d", rec.Code)
	}
}

func TestSearch_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewSearchHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/search",
		strings.NewReader(`{"query":"hello"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Search(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != false {
		t.Errorf("expected ok=false, got %v", env["ok"])
	}
}
