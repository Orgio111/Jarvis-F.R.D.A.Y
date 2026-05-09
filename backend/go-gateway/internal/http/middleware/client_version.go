package middleware

import (
	"context"
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
)

// ClientVersion validates and propagates the X-Client-Version header.
// Returns 400 if the header is missing or empty.
func ClientVersion(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		correlationID := GetCorrelationID(r)

		clientVersion := r.Header.Get("X-Client-Version")
		if clientVersion == "" {
			contracts.WriteBadRequest(w, correlationID, "missing_client_version",
				"X-Client-Version header is required")
			return
		}

		ctx := context.WithValue(r.Context(), ClientVersionKey, clientVersion)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}
