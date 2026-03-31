// oauth_handler.go — Google OAuth2 flow handlers for the Gateway
//
// Routes (registered in cmd/gateway/main.go, NO auth middleware):
//
//	GET /auth/google              → redirect to Google consent screen
//	GET /auth/google/callback     → exchange code, upsert user in DB, issue JWT, set cookie
//
// Flow:
//  1. Browser → GET /auth/google
//  2. Gateway → 302 to accounts.google.com with state + PKCE
//  3. Google → 302 back to /auth/google/callback?code=...&state=...
//  4. Gateway → exchange code → get email + sub from Google userinfo API
//  5. Gateway → upsert user row in users table (by google_sub)
//  6. Gateway → issue RS256 access and refresh JWTs, set HttpOnly cookies, redirect to /dashboard
//  POST /auth/refresh            → exchange refresh token for new access token
package handler

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/auth"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// OAuthHandler handles the Google OAuth2 login flow.
type OAuthHandler struct {
	authSvc *auth.Service
	db      *db.Pool
}

func NewOAuthHandler(authSvc *auth.Service, pool *db.Pool) *OAuthHandler {
	return &OAuthHandler{authSvc: authSvc, db: pool}
}

// GoogleLogin handles GET /auth/google
// Generates a random state token, stores it in a short-lived cookie, and
// redirects the browser to Google's OAuth consent screen.
func (h *OAuthHandler) GoogleLogin(c *fiber.Ctx) error {
	state, err := generateState()
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: "state gen failed"})
	}

	// Store state in a short-lived cookie to verify on callback
	c.Cookie(&fiber.Cookie{
		Name:     "oauth_state",
		Value:    state,
		MaxAge:   300, // 5 minutes
		HTTPOnly: true,
		SameSite: "Lax",
		Secure:   false, // set true in production behind TLS
	})

	url := h.authSvc.GoogleAuthURL(state)
	return c.Redirect(url, fiber.StatusTemporaryRedirect)
}

// GoogleCallback handles GET /auth/google/callback
// Validates state, exchanges OAuth code, upserts user in DB, issues JWT.
func (h *OAuthHandler) GoogleCallback(c *fiber.Ctx) error {
	log := logger.L().With(zap.String("handler", "GoogleCallback"))

	// 1. Validate state — prevent CSRF
	cookieState := c.Cookies("oauth_state")
	queryState := c.Query("state")
	if cookieState == "" || cookieState != queryState {
		log.Warn("state mismatch", zap.String("cookie", cookieState), zap.String("query", queryState))
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Code: 400, Error: "invalid oauth state"})
	}
	// Clear state cookie
	c.Cookie(&fiber.Cookie{Name: "oauth_state", MaxAge: -1})

	// 2. Exchange code for user info
	code := c.Query("code")
	if code == "" {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Code: 400, Error: "missing code"})
	}

	googleSub, email, displayName, err := h.authSvc.GoogleUserInfo(c.Context(), code)
	if err != nil {
		log.Error("google userinfo failed", zap.Error(err))
		return c.Status(fiber.StatusUnauthorized).JSON(ErrorResponse{Code: 401, Error: "google auth failed"})
	}

	// 3. Upsert user in DB — create on first login, update name on subsequent logins
	userID, tenantID, err := h.upsertUser(c.Context(), googleSub, email, displayName)
	if err != nil {
		log.Error("user upsert failed", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: "user creation failed"})
	}

	// 4. Issue access and refresh JWTs
	accessToken, refreshToken, err := h.authSvc.IssueTokens(userID, tenantID, email, "user")
	if err != nil {
		log.Error("jwt issue failed", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: "token issue failed"})
	}

	// 5. Set HttpOnly JWT cookies (access: 15m, refresh: 7d)
	c.Cookie(&fiber.Cookie{
		Name:     "auth_token",
		Value:    accessToken,
		Expires:  time.Now().Add(15 * time.Minute),
		HTTPOnly: true,
		SameSite: "Lax",
		Secure:   false, // set true behind TLS in production
	})
	
	c.Cookie(&fiber.Cookie{
		Name:     "refresh_token",
		Value:    refreshToken,
		Expires:  time.Now().Add(7 * 24 * time.Hour),
		HTTPOnly: true,
		SameSite: "Lax",
		Secure:   false, // set true behind TLS in production
	})

	log.Info("google login success",
		zap.String("email", email),
		zap.String("user_id", userID),
	)

	// 6. Redirect to dashboard
	return c.Redirect("/dashboard", fiber.StatusTemporaryRedirect)
}

// upsertUser calls the upsert_google_user() Postgres function (migration 003).
// It atomically creates a personal tenant if needed, then upserts the user row.
// Returns (userID, tenantID) ready for JWT issuance.
func (h *OAuthHandler) upsertUser(ctx context.Context, googleSub, email, displayName string) (userID, tenantID string, err error) {
	row := h.db.QueryRow(ctx,
		`SELECT user_id::text, tenant_id::text FROM upsert_google_user($1, $2, $3)`,
		googleSub, email, displayName,
	)
	err = row.Scan(&userID, &tenantID)
	return userID, tenantID, err
}

// generateState returns a 16-byte random hex string for OAuth state.
func generateState() (string, error) {
	b := make([]byte, 16)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

// RefreshToken handles POST /auth/refresh
// Validates the refresh_token cookie and issues a new auth_token cookie.
func (h *OAuthHandler) RefreshToken(c *fiber.Ctx) error {
	log := logger.L().With(zap.String("handler", "RefreshToken"))
	
	refreshTokenStr := c.Cookies("refresh_token")
	if refreshTokenStr == "" {
		return c.Status(fiber.StatusUnauthorized).JSON(ErrorResponse{Code: 401, Error: "missing refresh token"})
	}

	claims, err := h.authSvc.ValidateToken(refreshTokenStr)
	if err != nil {
		log.Warn("refresh token validation failed", zap.Error(err))
		return c.Status(fiber.StatusUnauthorized).JSON(ErrorResponse{Code: 401, Error: "invalid refresh token"})
	}

	if claims.TokenType != "refresh" {
		log.Warn("invalid token type for refresh", zap.String("type", claims.TokenType))
		return c.Status(fiber.StatusUnauthorized).JSON(ErrorResponse{Code: 401, Error: "expected refresh token"})
	}

	// Issue new tokens (rolling refresh token)
	accessToken, newRefreshToken, err := h.authSvc.IssueTokens(claims.UserID, claims.TenantID, claims.Email, claims.Role)
	if err != nil {
		log.Error("token issue failed on refresh", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: "failed to issue new tokens"})
	}

	c.Cookie(&fiber.Cookie{
		Name:     "auth_token",
		Value:    accessToken,
		Expires:  time.Now().Add(15 * time.Minute),
		HTTPOnly: true,
		SameSite: "Lax",
		Secure:   false,
	})
	
	c.Cookie(&fiber.Cookie{
		Name:     "refresh_token",
		Value:    newRefreshToken,
		Expires:  time.Now().Add(7 * 24 * time.Hour),
		HTTPOnly: true,
		SameSite: "Lax",
		Secure:   false,
	})

	return c.JSON(fiber.Map{"status": "ok"})
}
