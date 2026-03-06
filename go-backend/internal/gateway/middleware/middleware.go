// Package middleware contains Fiber middleware for the API Gateway.
//
// Auth modes:
//   - SaaS  (AUTH_DISABLED unset / false): Google OAuth → RS256 JWT cookie
//   - Local (AUTH_DISABLED=true):          No login — static local user injected
package middleware

import (
	"os"
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/auth"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// LocalMode returns true when AUTH_DISABLED=true is set in the environment.
// Used by main.go to decide which auth middleware to install.
func LocalMode() bool {
	return strings.ToLower(os.Getenv("AUTH_DISABLED")) == "true"
}

// LocalAuth injects a fixed single-user identity into every request.
// This is the local/self-hosted mode — no login required.
// All projects go to user_id=local-user, tenant_id=local-tenant.
func LocalAuth() fiber.Handler {
	return func(c *fiber.Ctx) error {
		c.Locals("user_id", "00000000-0000-0000-0000-000000000001") // stable UUID for DB FKs
		c.Locals("tenant_id", "00000000-0000-0000-0000-000000000002")
		c.Locals("email", os.Getenv("LOCAL_USER_EMAIL"))
		c.Locals("role", "owner")
		return c.Next()
	}
}

// RequestLogger logs every HTTP request with method, path, status, latency, and trace ID.
func RequestLogger() fiber.Handler {
	return func(c *fiber.Ctx) error {
		start := time.Now()

		// attach trace ID before processing
		traceID := c.Get("X-Trace-ID")
		if traceID == "" {
			traceID = uuid.NewString()
		}
		c.Locals("trace_id", traceID)
		c.Set("X-Trace-ID", traceID)

		err := c.Next()
		latency := time.Since(start)

		fields := []zap.Field{
			zap.String("method", c.Method()),
			zap.String("path", c.Path()),
			zap.Int("status", c.Response().StatusCode()),
			zap.Duration("latency", latency),
			zap.String("ip", c.IP()),
			zap.String("trace_id", traceID),
		}

		if err != nil {
			logger.L().Error("request error", append(fields, zap.Error(err))...)
		} else if c.Response().StatusCode() >= 500 {
			logger.L().Error("server error", fields...)
		} else {
			logger.L().Info("request", fields...)
		}
		return err
	}
}

// JWTAuth validates the JWT from either:
//
//	a) Authorization: Bearer <token>  header (API clients / mobile)
//	b) auth_token cookie              (browsers after Google OAuth redirect)
//
// Skip paths: /healthz, /readyz, /metrics, /auth/*
func JWTAuth(authSvc *auth.Service) fiber.Handler {
	skipPaths := map[string]bool{
		"/healthz": true,
		"/readyz":  true,
		"/metrics": true,
	}

	return func(c *fiber.Ctx) error {
		path := c.Path()

		// Skip auth-less paths
		if skipPaths[path] || strings.HasPrefix(path, "/auth/") {
			return c.Next()
		}

		// 1. Try Authorization header (API / mobile clients)
		tokenStr := ""
		if authHeader := c.Get("Authorization"); strings.HasPrefix(authHeader, "Bearer ") {
			tokenStr = strings.TrimPrefix(authHeader, "Bearer ")
		}

		// 2. Fall back to HttpOnly cookie (browsers after Google OAuth)
		if tokenStr == "" {
			tokenStr = c.Cookies("auth_token")
		}

		if tokenStr == "" {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":    "authentication required",
				"trace_id": c.Locals("trace_id"),
			})
		}

		claims, err := authSvc.ValidateToken(tokenStr)
		if err != nil {
			logger.L().Warn("jwt validation failed",
				zap.String("error", err.Error()),
				zap.String("trace_id", c.Locals("trace_id").(string)),
			)
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":    "invalid or expired token",
				"trace_id": c.Locals("trace_id"),
			})
		}

		c.Locals("user_id", claims.UserID)
		c.Locals("tenant_id", claims.TenantID)
		c.Locals("email", claims.Email)
		c.Locals("role", claims.Role)

		return c.Next()
	}
}

// RequireRole returns a middleware that enforces minimum role access.
// Roles (ascending privilege): viewer < member < admin < owner
func RequireRole(minRole string) fiber.Handler {
	roleRank := map[string]int{
		"viewer": 1, "member": 2, "admin": 3, "owner": 4,
	}
	return func(c *fiber.Ctx) error {
		role, _ := c.Locals("role").(string)
		if roleRank[role] < roleRank[minRole] {
			return c.Status(fiber.StatusForbidden).JSON(fiber.Map{
				"error": "insufficient permissions",
			})
		}
		return c.Next()
	}
}

// RateLimiter applies an in-memory token bucket rate limit.
// For distributed enforcement across pods, swap with Redis sliding window.
func RateLimiter(maxRPS int) fiber.Handler {
	type entry struct {
		tokens    float64
		lastCheck time.Time
	}
	// NOTE: In production, replace with Redis sliding window (see redisclient.SlidingWindowLimit)
	// This in-memory version works per-pod and is fine for initial deployment.
	store := make(map[string]*entry)
	var mu sync.Mutex

	return func(c *fiber.Ctx) error {
		// Use user_id from JWT if available, fall back to IP
		key, _ := c.Locals("user_id").(string)
		if key == "" {
			key = c.IP()
		}

		mu.Lock()
		defer mu.Unlock()

		now := time.Now()
		e, exists := store[key]
		if !exists {
			e = &entry{tokens: float64(maxRPS), lastCheck: now}
			store[key] = e
		}

		// Refill tokens based on time elapsed
		elapsed := now.Sub(e.lastCheck)
		e.tokens += elapsed.Seconds() * float64(maxRPS)
		if e.tokens > float64(maxRPS) {
			e.tokens = float64(maxRPS)
		}
		e.lastCheck = now

		if e.tokens < 1 {
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error": "rate limit exceeded",
			})
		}

		e.tokens--
		return c.Next()
	}
}

// CORS sets permissive headers for local development.
// In production, restrict AllowOrigins to your actual domain.
func CORS() fiber.Handler {
	return func(c *fiber.Ctx) error {
		c.Set("Access-Control-Allow-Origin", "*")
		c.Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Trace-ID")

		if c.Method() == "OPTIONS" {
			return c.SendStatus(fiber.StatusNoContent)
		}
		return c.Next()
	}
}
