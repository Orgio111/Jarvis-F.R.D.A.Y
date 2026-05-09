package middleware

import (
	"net/http"
	"strings"
)

// CORS returns a middleware that sets CORS headers allowing the configured origins.
func CORS(allowedOrigins []string) func(http.Handler) http.Handler {
	originSet := make(map[string]struct{}, len(allowedOrigins))
	for _, o := range allowedOrigins {
		originSet[strings.TrimSpace(o)] = struct{}{}
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			origin := r.Header.Get("Origin")
			if _, allowed := originSet[origin]; allowed {
				w.Header().Set("Access-Control-Allow-Origin", origin)
				w.Header().Set("Access-Control-Allow-Credentials", "true")
				w.Header().Set("Vary", "Origin")
			}

			w.Header().Set("Access-Control-Allow-Methods",
				"GET, POST, PUT, PATCH, DELETE, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers",
				"Content-Type, Authorization, X-Request-ID, X-Session-ID, X-Client-Version, X-Correlation-ID")
			w.Header().Set("Access-Control-Expose-Headers",
				"X-Request-ID, X-Correlation-ID, X-Session-ID")
			w.Header().Set("Access-Control-Max-Age", "86400")

			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusNoContent)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}
