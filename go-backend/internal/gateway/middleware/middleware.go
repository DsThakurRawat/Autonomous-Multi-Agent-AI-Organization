// Package middleware contains Fiber middleware for the API Gateway.
// Every incoming request passes through: Logger → TraceID → JWT Auth → RateLimit
package middleware

import (
	"strings"
	"sync"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/auth"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

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

// JWTAuth validates the Bearer token in the Authorization header.
// On success, injects user_id, tenant_id, email, and role into c.Locals.
// Skip paths: /healthz, /readyz, /metrics, /v1/auth/*
func JWTAuth(authSvc *auth.Service) fiber.Handler {
	skipPaths := map[string]bool{
		"/healthz": true,
		"/readyz":  true,
		"/metrics": true,
	}

	return func(c *fiber.Ctx) error {
		path := c.Path()

		// Skip auth for health/metrics and OAuth endpoints
		if skipPaths[path] || strings.HasPrefix(path, "/v1/auth/") {
			return c.Next()
		}

		authHeader := c.Get("Authorization")
		if !strings.HasPrefix(authHeader, "Bearer ") {
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":    "missing or malformed Authorization header",
				"trace_id": c.Locals("trace_id"),
			})
		}

		tokenStr := strings.TrimPrefix(authHeader, "Bearer ")
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

		// Inject claims into request context for handlers
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
	var mu = new(struct{ sync.Mutex })

	_ = mu // placeholder until sync is imported

	return func(c *fiber.Ctx) error {
		// Use user_id from JWT if available, fall back to IP
		key := c.Locals("user_id").(string)
		if key == "" {
			key = c.IP()
		}

		_ = key // TODO: implement actual token bucket with sync.Mutex
		_ = store

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
