// Package middleware contains Fiber middleware for the API Gateway.
//
// Auth modes:
//   - SaaS  (AUTH_DISABLED unset / false): Google OAuth → RS256 JWT cookie
//   - Local (AUTH_DISABLED=true):          No login — static local user injected
package middleware

import (
	"os"
	"strings"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/auth"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	redisclient "github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/redis"
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

		if claims.TokenType != "access" {
			logger.L().Warn("wrong token type presented to API",
				zap.String("type", claims.TokenType),
				zap.String("trace_id", c.Locals("trace_id").(string)),
			)
			return c.Status(fiber.StatusUnauthorized).JSON(fiber.Map{
				"error":    "expected access token",
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

// DistributedRateLimiter applies a Redis-backed sliding window rate limit.
func DistributedRateLimiter(rc *redisclient.Client, limit int64, window time.Duration) fiber.Handler {
	return func(c *fiber.Ctx) error {
		key, _ := c.Locals("user_id").(string)
		if key == "" {
			key = c.IP()
		}
		key = "rate_limit:" + key

		allowed, count, err := rc.SlidingWindowLimit(c.Context(), key, limit, window)
		if err != nil {
			logger.L().Error("redis rate limit error", zap.Error(err))
			return c.Next() // Fail open to avoid blocking users
		}

		if !allowed {
			logger.L().Warn("rate limit exceeded", zap.String("key", key), zap.Int64("count", count))
			return c.Status(fiber.StatusTooManyRequests).JSON(fiber.Map{
				"error": "rate limit exceeded",
				"limit": limit,
			})
		}

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
