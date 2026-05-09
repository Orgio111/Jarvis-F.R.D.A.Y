package middleware

import (
	"context"
	"net/http"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
)

// Session validates and propagates the X-Session-ID header.
// Returns 400 if the header is missing or empty.
func Session(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		correlationID := GetCorrelationID(r)

		sessionID := r.Header.Get("X-Session-ID")
		if sessionID == "" {
			contracts.WriteBadRequest(w, correlationID, "missing_session_id",
				"X-Session-ID header is required")
			return
		}

		ctx := context.WithValue(r.Context(), SessionIDKey, sessionID)
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}
