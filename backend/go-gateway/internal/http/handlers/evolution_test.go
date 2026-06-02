package handlers_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/orgio111/jarvis/go-gateway/internal/http/handlers"
)

// ─── SelfImprovementHandler (evolution.go) ────────────────────────────────────

func TestSelfImprovementStatus_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/self-improvement/status", nil)
	rec := httptest.NewRecorder()
	h.Status(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 fallback, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != true {
		t.Errorf("expected ok=true, got %v", env["ok"])
	}
	data, ok := env["data"].(map[string]interface{})
	if !ok {
		t.Fatalf("data is not an object: %T", env["data"])
	}
	if data["enabled"] != false {
		t.Errorf("expected enabled=false fallback, got %v", data["enabled"])
	}
}

func TestSelfImprovementStatus_ServiceUp(t *testing.T) {
	payload := map[string]interface{}{"enabled": true, "pendingSuggestions": 3.0, "appliedCount": 7.0}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/self-improvement/status", nil)
	rec := httptest.NewRecorder()
	h.Status(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestSelfImprovementListSuggestions_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/self-improvement/suggestions", nil)
	rec := httptest.NewRecorder()
	h.ListSuggestions(rec, req)

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

func TestSelfImprovementListSuggestions_ServiceUp(t *testing.T) {
	payload := map[string]interface{}{"suggestions": []interface{}{}, "total": 0.0}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/self-improvement/suggestions", nil)
	rec := httptest.NewRecorder()
	h.ListSuggestions(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestSelfImprovementSuggest_InvalidJSON(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggest",
		strings.NewReader(`not-json`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Suggest(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400 for invalid JSON, got %d", rec.Code)
	}
}

func TestSelfImprovementSuggest_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggest",
		strings.NewReader(`{"content":"test suggestion"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Suggest(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != false {
		t.Errorf("expected ok=false, got %v", env["ok"])
	}
}

func TestSelfImprovementSuggest_UpstreamError(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		w.Write([]byte(`{"ok":false,"error":{"code":"suggestion_error","message":"failed to create"}}`))
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggest",
		strings.NewReader(`{"content":"test"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Suggest(rec, req)

	// Handler checks err != nil first → returns 503 (service unavailable)
	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503 from upstream error, got %d", rec.Code)
	}
}

func TestSelfImprovementSuggest_Success(t *testing.T) {
	payload := map[string]interface{}{"id": "sugg-1", "content": "test", "status": "pending"}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggest",
		strings.NewReader(`{"content":"test"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Suggest(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestSelfImprovementApprove_Success(t *testing.T) {
	payload := map[string]interface{}{"id": "sugg-1", "status": "approved"}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggestions/sugg-1/approve", nil)
	rec := httptest.NewRecorder()
	h.Approve(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestSelfImprovementApprove_NotFound(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggestions/unknown/approve", nil)
	rec := httptest.NewRecorder()
	h.Approve(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestSelfImprovementReject_Success(t *testing.T) {
	payload := map[string]interface{}{"id": "sugg-1", "status": "rejected"}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggestions/sugg-1/reject", nil)
	rec := httptest.NewRecorder()
	h.Reject(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestSelfImprovementReject_NotFound(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggestions/unknown/reject", nil)
	rec := httptest.NewRecorder()
	h.Reject(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestSelfImprovementApprove_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
	}))
	h := handlers.NewSelfImprovementHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/self-improvement/suggestions/sugg-1/approve", nil)
	rec := httptest.NewRecorder()
	h.Approve(rec, req)

	// Handler calls WriteInternalError → ok=false
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != false {
		t.Errorf("expected ok=false on internal error, got %v", env["ok"])
	}
}
