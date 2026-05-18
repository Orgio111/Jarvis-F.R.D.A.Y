package middleware

import (
	"net/http"
	"os"
	"strings"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
)

// APIKey validates the Authorization: Bearer <token> header.
//
// Key resolution (checked in order):
//  1. GATEWAY_API_KEY   — primary key (legacy single-key setup)
//  2. GATEWAY_API_KEY_1 — primary key for dual-key rotation
//  3. GATEWAY_API_KEY_2 — secondary key for dual-key rotation
//
// Any non-empty key from the above set is accepted, enabling zero-downtime
// key rotation: deploy the new key as _KEY_2 while _KEY_1 is still live,
// then remove _KEY_1 once all clients have migrated.
//
// If NO key is configured the middleware is a no-op (dev mode).
func APIKey(next http.Handler) http.Handler {
	validKeys := loadAPIKeys()
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Dev mode — no keys configured.
		if len(validKeys) == 0 {
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
		if !validKeys[token] {
			contracts.WriteError(w, correlationID, http.StatusUnauthorized,
				"invalid_api_key", "Invalid API key", nil)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// loadAPIKeys reads GATEWAY_API_KEY, GATEWAY_API_KEY_1, and GATEWAY_API_KEY_2
// and returns a set of all non-empty values.
func loadAPIKeys() map[string]bool {
	keys := map[string]bool{}
	for _, envVar := range []string{"GATEWAY_API_KEY", "GATEWAY_API_KEY_1", "GATEWAY_API_KEY_2"} {
		if v := strings.TrimSpace(os.Getenv(envVar)); v != "" {
			keys[v] = true
		}
	}
	return keys
}
