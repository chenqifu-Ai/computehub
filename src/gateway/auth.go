// Package gateway provides authentication middleware for ComputeHub.
// Currently: Bearer token auth (lightweight, no external JWT dependency).
// Future: JWT with signing (RS256/HS256) when Go module dependencies are added.
package gateway

import (
	"net/http"
	"strings"
)

// ── Auth config ────────────────────────────────────────────────────
// Public paths that skip authentication.
var PublicPaths = []string{
	"/api/health",
	"/api/status",
	"/metrics",
	"/api/v1/upgrade/check",
	"/api/v1/upgrade/config",
	"/api/v1/upgrade/checksum",
}

// AuthMiddleware returns an http.Handler wrapper that requires
// Authorization: Bearer <token> for all non-public endpoints.
// If AuthBearerToken is empty, authentication is bypassed (dev mode).
var AuthBearerToken string // set from main.go via env var AUTH_BEARER_TOKEN

func AuthMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Skip auth for public paths
		for _, p := range PublicPaths {
			if r.URL.Path == p || strings.HasPrefix(r.URL.Path, p+"/") {
				next.ServeHTTP(w, r)
				return
			}
		}

		// Dev mode: no token required
		if AuthBearerToken == "" {
			logWithTimestamp("⚠️  Auth bypass: AUTH_BEARER_TOKEN not set (dev mode)")
			next.ServeHTTP(w, r)
			return
		}

		// Check Authorization header
		auth := r.Header.Get("Authorization")
		if auth == "" {
			http.Error(w, `{"error":"missing Authorization header"}`, http.StatusUnauthorized)
			return
		}

		if !strings.HasPrefix(auth, "Bearer ") {
			http.Error(w, `{"error":"use 'Bearer <token>' format"}`, http.StatusUnauthorized)
			return
		}

		token := strings.TrimPrefix(auth, "Bearer ")
		if token != AuthBearerToken {
			http.Error(w, `{"error":"invalid token"}`, http.StatusUnauthorized)
			return
		}

		next.ServeHTTP(w, r)
	})
}

// AuthMiddlewareFunc is the Func variant for ServeMux-style registration.
func AuthMiddlewareFunc(next http.HandlerFunc) http.HandlerFunc {
	return AuthMiddleware(http.HandlerFunc(next)).ServeHTTP
}
