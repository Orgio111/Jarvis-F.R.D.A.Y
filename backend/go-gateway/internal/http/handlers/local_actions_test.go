package handlers_test

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/orgio111/jarvis/go-gateway/internal/http/handlers"
)

func TestLocalActions_ListFallback(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/local-actions", nil)
	rec := httptest.NewRecorder()
	h.List(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200 fallback, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != true {
		t.Errorf("expected ok=true, got %v", env["ok"])
	}
}

func TestLocalActions_PendingFallback(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/local-actions/pending", nil)
	rec := httptest.NewRecorder()
	h.ListPending(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200 fallback, got %d", rec.Code)
	}
}

func TestLocalActions_ListSuccess(t *testing.T) {
	data := map[string]interface{}{"actions": []interface{}{}, "total": 0.0, "enabled": true}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(data))
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/local-actions", nil)
	rec := httptest.NewRecorder()
	h.List(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200, got %d", rec.Code)
	}
}
