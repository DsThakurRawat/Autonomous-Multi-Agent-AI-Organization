package server

import (
	"context"
	"time"

	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// LeaseMonitor scans for dead tasks (running but no active Redis lease).
type LeaseMonitor struct {
	db    *db.Pool
	redis *db.Redis
}

func NewLeaseMonitor(pool *db.Pool, rds *db.Redis) *LeaseMonitor {
	return &LeaseMonitor{
		db:    pool,
		redis: rds,
	}
}

// Start runs the monitor loop until context is cancelled.
func (m *LeaseMonitor) Start(ctx context.Context, interval time.Duration) {
	log := logger.L()
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	log.Info("lease monitor started", zap.Duration("interval", interval))

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			m.checkLeases(ctx)
		}
	}
}

func (m *LeaseMonitor) checkLeases(ctx context.Context) {
	log := logger.L()

	// Find all tasks that are currently "running" according to the DB
	query := `SELECT id, project_id, name FROM tasks WHERE status = 'running'`
	rows, err := m.db.Query(ctx, query)
	if err != nil {
		log.Error("lease_monitor: task lookup failed", zap.Error(err))
		return
	}
	defer rows.Close()

	for rows.Next() {
		var taskID, projectID, taskName string
		if err := rows.Scan(&taskID, &projectID, &taskName); err != nil {
			continue
		}

		// Check if lease exists in Redis
		leased, err := m.redis.IsTaskLeased(ctx, taskID)
		if err != nil {
			log.Warn("lease_monitor: redis check failed", zap.String("task_id", taskID), zap.Error(err))
			continue
		}

		if !leased {
			// LEASE EXPIRED!
			// Mark task as failed in DB
			log.Warn("LEASE EXPIRED: task heartbeat lost",
				zap.String("task_id", taskID),
				zap.String("project_id", projectID),
				zap.String("task_name", taskName),
			)

			updateQuery := `UPDATE tasks SET status = 'failed', error_message = 'Agent heartbeat lost (Lease Expired)' WHERE id = $1`
			_, err = m.db.Exec(ctx, updateQuery, taskID)
			if err != nil {
				log.Error("lease_monitor: failed to mark task as failed", zap.Error(err))
				continue
			}

			// Optionally: Implement re-dispatch logic here if max_retries > 0
		}
	}
}
