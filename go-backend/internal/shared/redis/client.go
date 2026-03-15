// Package redisclient provides a Redis client with cluster support,
// helper methods for common patterns, and health checking.
package redisclient

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// Client wraps redis.UniversalClient (works for both single-node and cluster).
type Client struct {
	redis.UniversalClient
}

// New creates a Redis client. If cfg.Cluster is true, uses ClusterClient;
// otherwise a single-node client. Pings on creation.
func New(ctx context.Context, cfg *config.RedisConfig) (*Client, error) {
	var addrs []string
	if cfg.Cluster {
		addrs = strings.Split(cfg.Addr, ",")
	} else {
		addrs = []string{cfg.Addr}
	}

	client := redis.NewUniversalClient(&redis.UniversalOptions{
		Addrs:       addrs,
		Password:    cfg.Password,
		DB:          cfg.DB,
		DialTimeout: 5 * time.Second,
		ReadTimeout: 3 * time.Second,
		WriteTimeout: 3 * time.Second,
	})

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := client.Ping(pingCtx).Err(); err != nil {
		return nil, fmt.Errorf("redis: ping failed: %w", err)
	}

	logger.L().Info("redis connected", zap.String("addr", cfg.Addr), zap.Bool("cluster", cfg.Cluster))
	return &Client{client}, nil
}

// SetJSON serialises val to JSON and stores it with optional TTL.
// Uses MarshalJSON if val implements it, otherwise falls back to fmt.Sprintf.
func (c *Client) SetJSON(ctx context.Context, key string, val any, ttl time.Duration) error {
	data, err := json.Marshal(val)
	if err != nil {
		return fmt.Errorf("redis: marshal: %w", err)
	}
	return c.Set(ctx, key, data, ttl).Err()
}

// GetString returns a string value or ("", false) if key is absent.
func (c *Client) GetString(ctx context.Context, key string) (string, bool, error) {
	val, err := c.Get(ctx, key).Result()
	if err == redis.Nil {
		return "", false, nil
	}
	if err != nil {
		return "", false, err
	}
	return val, true, nil
}

// Publish sends msg to a Redis Pub/Sub channel.
func (c *Client) Publish(ctx context.Context, channel, msg string) error {
	return c.Do(ctx, "PUBLISH", channel, msg).Err()
}

// Subscribe returns a PubSub connection to the given channel.
func (c *Client) Subscribe(ctx context.Context, channel string) *redis.PubSub {
	return c.UniversalClient.Subscribe(ctx, channel)
}

// IncrBy atomically increments a key. Returns new value.
func (c *Client) IncrBy(ctx context.Context, key string, val int64) (int64, error) {
	return c.Do(ctx, "INCRBY", key, val).Int64()
}

// SlidingWindowLimit enforces a rate limit using a sorted set sliding window.
// Returns (allowed bool, count int64, err).
func (c *Client) SlidingWindowLimit(ctx context.Context, key string, limit int64, window time.Duration) (bool, int64, error) {
	now := time.Now()
	windowStart := now.Add(-window).UnixMilli()
	nowMs := now.UnixMilli()

	pipe := c.Pipeline()
	pipe.ZRemRangeByScore(ctx, key, "0", fmt.Sprintf("%d", windowStart))
	pipe.ZAdd(ctx, key, redis.Z{Score: float64(nowMs), Member: nowMs})
	pipe.ZCard(ctx, key)
	pipe.Expire(ctx, key, window+time.Second)

	results, err := pipe.Exec(ctx)
	if err != nil {
		return false, 0, err
	}

	count := results[2].(*redis.IntCmd).Val()
	return count <= limit, count, nil
}
