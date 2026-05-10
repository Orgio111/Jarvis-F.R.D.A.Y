package handlers_test

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/orgio111/jarvis/go-gateway/internal/http/handlers"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// stubPythonServer returns a test server that responds to /health
func stubPythonServer(t *testing.T) *httptest.Server {
	t.Helper()
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"ok":true,"data":{"status":"pass","version":"test"}}`))
	})
	return httptest.NewServer(mux)
}

func TestHealthHandler_Pass(t *testing.T) {
	stub := stubPythonServer(t)
	defer stub.Close()

	aiProxy := proxy.New(stub.URL, 5*time.Second)
	h := handlers.NewHealthHandler(aiProxy, nil)

	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	req.Header.Set("X-Correlation-ID", "test-corr")
	rr := httptest.NewRecorder()

	h.ServeHTTP(rr, req)

	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rr.Code)
	}

	var body map[string]interface{}
	if err := json.NewDecoder(rr.Body).Decode(&body); err != nil {
		t.Fatalf("decode error: %v", err)
	}
	if body["ok"] != true {
		t.Errorf("expected ok=true, got %v", body["ok"])
	}
	data, ok := body["data"].(map[string]interface{})
	if !ok {
		t.Fatalf("data is not an object: %T", body["data"])
	}
	if data["status"] == nil {
		t.Error("expected data.status to be set")
	}
}

func TestHealthHandler_PythonDown(t *testing.T) {
	// Point at a closed server so the python check fails
	aiProxy := proxy.New("http://127.0.0.1:1", 500*time.Millisecond) // port 1 is always refused
	h := handlers.NewHealthHandler(aiProxy, nil)

	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rr := httptest.NewRecorder()

	h.ServeHTTP(rr, req)

	// Should still return 200 with ok=true but status=warn
	if rr.Code != http.StatusOK {
		t.Fatalf("expected 200 even when python is down, got %d", rr.Code)
	}
	var body map[string]interface{}
	_ = json.NewDecoder(rr.Body).Decode(&body)
	if body["ok"] != true {
		t.Errorf("expected ok=true envelope even when service down")
	}
}
