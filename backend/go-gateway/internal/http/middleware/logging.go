package middleware

import (
	"net/http"
	"time"

	"go.uber.org/zap"
)

type responseWriter struct {
	http.ResponseWriter
	status int
	size   int
}

func (rw *responseWriter) WriteHeader(status int) {
	rw.status = status
	rw.ResponseWriter.WriteHeader(status)
}

func (rw *responseWriter) Write(b []byte) (int, error) {
	n, err := rw.ResponseWriter.Write(b)
	rw.size += n
	return n, err
}

// RequestLogger logs every request with structured fields.
func RequestLogger(logger *zap.Logger) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			start := time.Now()
			rw := &responseWriter{ResponseWriter: w, status: http.StatusOK}

			next.ServeHTTP(rw, r)

			duration := time.Since(start)

			logger.Info("request",
				zap.String("method", r.Method),
				zap.String("path", r.URL.Path),
				zap.Int("status", rw.status),
				zap.Duration("duration", duration),
				zap.Int("responseBytes", rw.size),
				zap.String("correlationId", GetCorrelationID(r)),
				zap.String("sessionId", maskSessionID(GetSessionID(r))),
				zap.String("clientVersion", GetClientVersion(r)),
				zap.String("remoteAddr", r.RemoteAddr),
				zap.String("userAgent", r.UserAgent()),
			)
		})
	}
}

// maskSessionID shortens session ID for log output.
func maskSessionID(id string) string {
	if len(id) <= 8 {
		return id
	}
	return id[:8] + "..."
}
