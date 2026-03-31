package middleware

import (
	"fmt"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	redisclient "github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/redis"
)

// IdempotencyConfig defines configuration for the idempotency middleware.
type IdempotencyConfig struct {
	RedisClient *redisclient.Client
	TTL         time.Duration
}

// Idempotency applies an idempotency check based on the X-Idempotency-Key header.
func Idempotency(cfg IdempotencyConfig) fiber.Handler {
	if cfg.TTL == 0 {
		cfg.TTL = 24 * time.Hour
	}

	return func(c *fiber.Ctx) error {
		// Only apply to POST/PUT/DELETE
		if c.Method() == "GET" || c.Method() == "HEAD" || c.Method() == "OPTIONS" {
			return c.Next()
		}

		key := c.Get("X-Idempotency-Key")
		if key == "" {
			return c.Next()
		}

		// Namespace the key
		userID, _ := c.Locals("user_id").(string)
		redisKey := fmt.Sprintf("idempotency:%s:%s", userID, key)

		// 1. Check if key exists
		val, exists, err := cfg.RedisClient.GetString(c.Context(), redisKey)
		if err != nil {
			logger.L().Error("idempotency: redis get failed", zap.Error(err))
			return c.Next()
		}

		if exists {
			if val == "PENDING" {
				return c.Status(fiber.StatusConflict).JSON(fiber.Map{
					"error": "request is currently being processed",
				})
			}
			// Return cached response (Simple implementation for now: return 200 OK + generic msg)
			// In production, we'd store the full status code and body.
			return c.Status(fiber.StatusOK).JSON(fiber.Map{
				"message": "duplicate request detected",
				"status":  "idempotent_hit",
				"cached_response": val,
			})
		}

		// 2. Mark as PENDING
		err = cfg.RedisClient.Set(c.Context(), redisKey, "PENDING", cfg.TTL).Err()
		if err != nil {
			logger.L().Error("idempotency: redis set pending failed", zap.Error(err))
			return c.Next()
		}

		// 3. Process request
		err = c.Next()

		// 4. Update with result (simplified: store "COMPLETED" or error message)
		status := "COMPLETED"
		if err != nil {
			status = fmt.Sprintf("FAILED: %s", err.Error())
		}
		
		_ = cfg.RedisClient.Set(c.Context(), redisKey, status, cfg.TTL)
		
		return err
	}
}
