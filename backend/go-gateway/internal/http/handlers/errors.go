package handlers

import (
	"errors"
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
	"github.com/orgio111/jarvis/go-gateway/internal/proxy"
)

// writeProxyError writes the appropriate HTTP response for a proxy error.
// Distinguishes circuit-open (503 circuit_open) from generic errors.
func writeProxyError(w http.ResponseWriter, correlationID, service string, err error) {
	if errors.Is(err, proxy.ErrCircuitOpen) {
		contracts.WriteCircuitOpen(w, correlationID, service)
		return
	}
	contracts.WriteServiceUnavailable(w, correlationID, service)
}
