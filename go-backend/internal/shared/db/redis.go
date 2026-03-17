package db

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// Redis wraps either a single redis client or a cluster client
type Redis struct {
	Client redis.UniversalClient
}

// NewRedis creates a new Redis client based on the provided config.
func NewRedis(ctx context.Context, cfg *config.RedisConfig) (*Redis, error) {
	log := logger.L()

	var client redis.UniversalClient
	addrs := strings.Split(cfg.Addr, ",")

	if cfg.Cluster {
		client = redis.NewClusterClient(&redis.ClusterOptions{
			Addrs:    addrs,
			Password: cfg.Password,
		})
	} else {
		client = redis.NewClient(&redis.Options{
			Addr:     addrs[0],
			Password: cfg.Password,
			DB:       cfg.DB,
		})
	}

	// Ping to verify connection
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("redis: ping failed: %w", err)
	}

	log.Info("redis connected", zap.String("addr", cfg.Addr), zap.Bool("cluster", cfg.Cluster))
	return &Redis{Client: client}, nil
}

// Close closes the redis client
func (r *Redis) Close() error {
	return r.Client.Close()
}

// SetTaskLease marks a task as leased in Redis for a specific duration.
// Returns true if the lease was acquired (didn't exist or was updated).
func (r *Redis) SetTaskLease(ctx context.Context, taskID string, duration time.Duration) (bool, error) {
	key := fmt.Sprintf("task:lease:%s", taskID)
	// We use SetNX for initial acquisition or just Set with expiry for heartbeat renewal
	err := r.Client.Set(ctx, key, "active", duration).Err()
	if err != nil {
		return false, err
	}
	return true, nil
}

// IsTaskLeased checks if a task lease is still active in Redis
func (r *Redis) IsTaskLeased(ctx context.Context, taskID string) (bool, error) {
	key := fmt.Sprintf("task:lease:%s", taskID)
	exists, err := r.Client.Exists(ctx, key).Result()
	if err != nil {
		return false, err
	}
	return exists > 0, nil
}

// ClearTaskLease manually removes a lease (e.g., when task completes)
func (r *Redis) ClearTaskLease(ctx context.Context, taskID string) error {
	key := fmt.Sprintf("task:lease:%s", taskID)
	return r.Client.Del(ctx, key).Err()
}
