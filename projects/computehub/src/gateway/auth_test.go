package gateway

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAuthMiddleware_BypassInDevMode(t *testing.T) {
	// Ensure dev mode (empty token)
	AuthBearerToken = ""

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	authenticated := AuthMiddleware(handler)

	// No Authorization header should pass in dev mode
	req := httptest.NewRequest("GET", "/api/v1/tasks/submit", nil)
	rec := httptest.NewRecorder()

	authenticated.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200 in dev mode, got %d", rec.Code)
	}
}

func TestAuthMiddleware_ValidToken(t *testing.T) {
	AuthBearerToken = "test-secret-token"
	defer func() { AuthBearerToken = "" }()

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	authenticated := AuthMiddleware(handler)

	// Valid token
	req := httptest.NewRequest("GET", "/api/v1/tasks/submit", nil)
	req.Header.Set("Authorization", "Bearer test-secret-token")
	rec := httptest.NewRecorder()

	authenticated.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200 with valid token, got %d: %s", rec.Code, rec.Body.String())
	}
}

func TestAuthMiddleware_InvalidToken(t *testing.T) {
	AuthBearerToken = "test-secret-token"
	defer func() { AuthBearerToken = "" }()

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	authenticated := AuthMiddleware(handler)

	// Invalid token
	req := httptest.NewRequest("GET", "/api/v1/tasks/submit", nil)
	req.Header.Set("Authorization", "Bearer wrong-token")
	rec := httptest.NewRecorder()

	authenticated.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Errorf("expected 401 with invalid token, got %d", rec.Code)
	}
}

func TestAuthMiddleware_MissingToken(t *testing.T) {
	AuthBearerToken = "test-secret-token"
	defer func() { AuthBearerToken = "" }()

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	authenticated := AuthMiddleware(handler)

	// No auth header
	req := httptest.NewRequest("GET", "/api/v1/tasks/submit", nil)
	rec := httptest.NewRecorder()

	authenticated.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Errorf("expected 401 with no auth header, got %d", rec.Code)
	}
}

func TestAuthMiddleware_PublicPath(t *testing.T) {
	AuthBearerToken = "test-secret-token"
	defer func() { AuthBearerToken = "" }()

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	authenticated := AuthMiddleware(handler)

	// Health check is public
	req := httptest.NewRequest("GET", "/api/health", nil)
	rec := httptest.NewRecorder()

	authenticated.ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Errorf("expected 200 for public path /api/health, got %d", rec.Code)
	}
}

func TestAuthMiddleware_WrongAuthFormat(t *testing.T) {
	AuthBearerToken = "test-secret-token"
	defer func() { AuthBearerToken = "" }()

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	authenticated := AuthMiddleware(handler)

	// Wrong format (missing "Bearer ")
	req := httptest.NewRequest("GET", "/api/v1/tasks/submit", nil)
	req.Header.Set("Authorization", "test-secret-token")
	rec := httptest.NewRecorder()

	authenticated.ServeHTTP(rec, req)

	if rec.Code != http.StatusUnauthorized {
		t.Errorf("expected 401 for wrong auth format, got %d", rec.Code)
	}
}
