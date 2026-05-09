package middleware

import (
	"net/http"
	"sync"
	"time"

	"golang.org/x/time/rate"

	"github.com/orgio111/jarvis/go-gateway/internal/contracts"
)

type sessionLimiter struct {
	limiter  *rate.Limiter
	lastSeen time.Time
}

// RateLimiter returns a per-session-ID rate limiting middleware.
// Clients without a session ID (already rejected upstream) are not handled here.
func RateLimiter(requestsPerMinute int) func(http.Handler) http.Handler {
	mu := sync.Mutex{}
	limiters := make(map[string]*sessionLimiter)

	// Background cleanup of inactive sessions
	go func() {
		tick := time.NewTicker(5 * time.Minute)
		defer tick.Stop()
		for range tick.C {
			mu.Lock()
			threshold := time.Now().Add(-10 * time.Minute)
			for id, sl := range limiters {
				if sl.lastSeen.Before(threshold) {
					delete(limiters, id)
				}
			}
			mu.Unlock()
		}
	}()

	rps := rate.Limit(float64(requestsPerMinute) / 60.0)
	burst := requestsPerMinute / 10
	if burst < 1 {
		burst = 1
	}

	getLimiter := func(sessionID string) *rate.Limiter {
		mu.Lock()
		defer mu.Unlock()
		sl, exists := limiters[sessionID]
		if !exists {
			sl = &sessionLimiter{
				limiter: rate.NewLimiter(rps, burst),
			}
			limiters[sessionID] = sl
		}
		sl.lastSeen = time.Now()
		return sl.limiter
	}

	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			sessionID := r.Header.Get("X-Session-ID")
			if sessionID == "" {
				next.ServeHTTP(w, r)
				return
			}

			limiter := getLimiter(sessionID)
			if !limiter.Allow() {
				correlationID := GetCorrelationID(r)
				contracts.WriteError(w, correlationID, http.StatusTooManyRequests,
					"rate_limit_exceeded", "Request rate limit exceeded. Please slow down.", nil)
				return
			}

			next.ServeHTTP(w, r)
		})
	}
}
