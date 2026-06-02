package handlers_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/orgio111/jarvis/go-gateway/internal/http/handlers"
)

// ─── ToolsHandler ─────────────────────────────────────────────────────────────

func TestToolsList_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewToolsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/tools", nil)
	rec := httptest.NewRecorder()
	h.List(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200 fallback, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != true {
		t.Errorf("expected ok=true, got %v", env["ok"])
	}
}

func TestToolsList_Success(t *testing.T) {
	payload := map[string]interface{}{"tools": []interface{}{}, "total": 0.0, "enabled": 0.0}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewToolsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodGet, "/api/tools", nil)
	rec := httptest.NewRecorder()
	h.List(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestToolsExecute_InvalidBody(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {}))
	h := handlers.NewToolsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/tools/tool-1/execute",
		strings.NewReader(`not-json`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Execute(rec, req)

	if rec.Code != http.StatusBadRequest {
		t.Errorf("expected 400 for invalid JSON, got %d", rec.Code)
	}
}

func TestToolsExecute_NotFound(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	h := handlers.NewToolsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/tools/unknown/execute",
		strings.NewReader(`{}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Execute(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestToolsExecute_ServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewToolsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/tools/tool-1/execute",
		strings.NewReader(`{"arg":"val"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Execute(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != false {
		t.Errorf("expected ok=false, got %v", env["ok"])
	}
}

func TestToolsExecute_Success(t *testing.T) {
	payload := map[string]interface{}{"id": "tool-1", "result": "done"}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewToolsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/tools/tool-1/execute",
		strings.NewReader(`{"arg":"val"}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Execute(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

// ─── LocalActionsHandler (merged from local_actions.go → tools.go) ─────────────

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

func TestLocalActions_ExecuteNotFound(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/local-actions/unknown/execute",
		strings.NewReader(`{}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Execute(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestLocalActions_ExecuteServiceDown(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/local-actions/act-1/execute",
		strings.NewReader(`{}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Execute(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
	env := decodeEnvelope(t, rec.Body.Bytes())
	if env["ok"] != false {
		t.Errorf("expected ok=false, got %v", env["ok"])
	}
}

func TestLocalActions_ExecuteDisabled(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusServiceUnavailable)
		w.Write([]byte(`{"ok":false,"error":{"code":"pc_control_disabled"}}`))
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/local-actions/act-1/execute",
		strings.NewReader(`{}`))
	req.Header.Set("Content-Type", "application/json")
	rec := httptest.NewRecorder()
	h.Execute(rec, req)

	if rec.Code != http.StatusServiceUnavailable {
		t.Errorf("expected 503, got %d", rec.Code)
	}
}

func TestLocalActions_ApproveNotFound(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/local-actions/approvals/unknown/approve", nil)
	rec := httptest.NewRecorder()
	h.Approve(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestLocalActions_ApproveSuccess(t *testing.T) {
	payload := map[string]interface{}{"id": "app-1", "status": "approved"}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/local-actions/approvals/app-1/approve", nil)
	rec := httptest.NewRecorder()
	h.Approve(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestLocalActions_DenyNotFound(t *testing.T) {
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNotFound)
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/local-actions/approvals/unknown/deny", nil)
	rec := httptest.NewRecorder()
	h.Deny(rec, req)

	if rec.Code != http.StatusNotFound {
		t.Errorf("expected 404, got %d", rec.Code)
	}
}

func TestLocalActions_DenySuccess(t *testing.T) {
	payload := map[string]interface{}{"id": "app-1", "status": "denied"}
	p, url := newTestProxy(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write(okEnvelope(payload))
	}))
	h := handlers.NewLocalActionsHandler(newTestConfig(url), p)

	req := httptest.NewRequest(http.MethodPost, "/api/local-actions/approvals/app-1/deny", nil)
	rec := httptest.NewRecorder()
	h.Deny(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}
