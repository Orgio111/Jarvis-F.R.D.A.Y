package middleware

import (
	"net/http"
	"os"
	"strings"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
)

// APIKey validates the Authorization: Bearer <token> header against
// GATEWAY_API_KEY env var. If the env var is empty, auth is skipped
// (useful for local development — set it in production).
func APIKey(next http.Handler) http.Handler {
	secret := strings.TrimSpace(os.Getenv("GATEWAY_API_KEY"))
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Skip when no key is configured (dev mode).
		if secret == "" {
			next.ServeHTTP(w, r)
			return
		}

		correlationID := GetCorrelationID(r)

		authHeader := r.Header.Get("Authorization")
		if authHeader == "" {
			contracts.WriteError(w, correlationID, http.StatusUnauthorized,
				"missing_api_key", "Authorization header is required", nil)
			return
		}

		const prefix = "Bearer "
		if !strings.HasPrefix(authHeader, prefix) {
			contracts.WriteError(w, correlationID, http.StatusUnauthorized,
				"invalid_auth_scheme", "Use Authorization: Bearer <key>", nil)
			return
		}

		token := strings.TrimSpace(authHeader[len(prefix):])
		if token != secret {
			contracts.WriteError(w, correlationID, http.StatusUnauthorized,
				"invalid_api_key", "Invalid API key", nil)
			return
		}

		next.ServeHTTP(w, r)
	})
}
