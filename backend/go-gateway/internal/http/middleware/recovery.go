package middleware

import (
	"net/http"
	"runtime/debug"

	"go.uber.org/zap"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
)

// Recovery catches panics, logs them, and returns a 500 error envelope.
func Recovery(logger *zap.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			defer func() {
				if rec := recover(); rec != nil {
					correlationID := GetCorrelationID(r)
					logger.Error("panic recovered",
						zap.Any("panic", rec),
						zap.String("stack", string(debug.Stack())),
						zap.String("correlationId", correlationID),
						zap.String("method", r.Method),
						zap.String("path", r.URL.Path),
					)
					contracts.WriteInternalError(w, correlationID)
				}
			}()
			next.ServeHTTP(w, r)
		})
	}
}
