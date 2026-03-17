package health

import (
	"context"
	"time"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	"go.uber.org/zap"
)

// DependencyStatus represents the health of a single dependency.
type DependencyStatus struct {
	Name    string `json:"name"`
	Healthy bool   `json:"healthy"`
	Error   string `json:"error,omitempty"`
}

// HealthOrchestrator aggregates health from all system components.
type HealthOrchestrator struct {
	db    *db.Pool
	redis *db.Redis
}

// NewHealthOrchestrator creates a new instance.
func NewHealthOrchestrator(pool *db.Pool, rds *db.Redis) *HealthOrchestrator {
	return &HealthOrchestrator{
		db:    pool,
		redis: rds,
	}
}

// CheckAll performs a full system health check.
func (h *HealthOrchestrator) CheckAll(ctx context.Context) ([]DependencyStatus, bool) {
	var results []DependencyStatus
	allHealthy := true

	// 1. Check Postgres
	pgStatus := DependencyStatus{Name: "postgresql"}
	if err := h.db.Ping(ctx); err != nil {
		pgStatus.Healthy = false
		pgStatus.Error = err.Error()
		allHealthy = false
	} else {
		pgStatus.Healthy = true
	}
	results = append(results, pgStatus)

	// 2. Check Redis
	redisStatus := DependencyStatus{Name: "redis"}
	if err := h.redis.Client.Ping(ctx).Err(); err != nil {
		redisStatus.Healthy = false
		redisStatus.Error = err.Error()
		allHealthy = false
	} else {
		redisStatus.Healthy = true
	}
	results = append(results, redisStatus)

	logger.L().Debug("system health check performed", zap.Bool("healthy", allHealthy))
	return results, allHealthy
}

// WaitUntilReady blocks until all core dependencies are healthy or ctx expires.
func (h *HealthOrchestrator) WaitUntilReady(ctx context.Context, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		_, healthy := h.CheckAll(ctx)
		if healthy {
			return nil
		}

		if time.Now().After(deadline) {
			return ctx.Err()
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			continue
		}
	}
}
