package server

import (
	"context"
	"time"

	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/kafka"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// LeaseMonitor scans for dead tasks (running but no active Redis lease).
type LeaseMonitor struct {
	db       *db.Pool
	redis    *db.Redis
	producer *kafka.Producer
}

func NewLeaseMonitor(pool *db.Pool, rds *db.Redis, prod *kafka.Producer) *LeaseMonitor {
	return &LeaseMonitor{
		db:       pool,
		redis:    rds,
		producer: prod,
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
	query := `SELECT id, project_id, name, task_type, agent_role, input_data, trace_id, retry_count FROM tasks WHERE status = 'running'`
	rows, err := m.db.Query(ctx, query)
	if err != nil {
		log.Error("lease_monitor: task lookup failed", zap.Error(err))
		return
	}
	defer rows.Close()

	for rows.Next() {
		var taskID, projectID, taskName, taskType, agentRole, traceID string
		var inputData map[string]any
		var retryCount int

		if err := rows.Scan(&taskID, &projectID, &taskName, &taskType, &agentRole, &inputData, &traceID, &retryCount); err != nil {
			log.Warn("lease_monitor: row scan failed", zap.Error(err))
			continue
		}

		// Check if lease exists in Redis
		leased, err := m.redis.IsTaskLeased(ctx, taskID)
		if err != nil {
			log.Warn("lease_monitor: redis check failed", zap.String("task_id", taskID), zap.Error(err))
			continue
		}

		if !leased {
			// LEASE EXPIRED! Calculate whether to retry
			maxRetries := 3

			if retryCount < maxRetries {
				log.Warn("LEASE EXPIRED: task heartbeat lost, retrying",
					zap.String("task_id", taskID),
					zap.String("project_id", projectID),
					zap.Int("attempt", retryCount+1),
				)
				
				// Re-dispatch Logic
				updateQuery := `UPDATE tasks SET status = 'pending', retry_count = retry_count + 1 WHERE id = $1`
				if _, err := m.db.Exec(ctx, updateQuery, taskID); err != nil {
					log.Error("lease_monitor: failed to mark task for retry", zap.Error(err))
					continue
				}

				taskPayload := map[string]any{
					"task_id":     taskID,
					"task_name":   taskName,
					"task_type":   taskType,
					"agent_role":  agentRole,
					"project_id":  projectID,
					"trace_id":    traceID,
					"input_data":  inputData,
					"retry_count": retryCount + 1,
					"max_retries": maxRetries,
				}

				if m.producer != nil {
					_, _, err = m.producer.PublishJSON("ai-org-tasks", projectID, taskPayload)
					if err != nil {
						log.Error("lease_monitor: failed to republish task to kafka", zap.Error(err))
					}
				}

			} else {
				log.Error("LEASE EXPIRED: task heartbeat lost, max retries exhausted",
					zap.String("task_id", taskID),
					zap.String("project_id", projectID),
				)

				// Exhausted max retries
				updateQuery := `UPDATE tasks SET status = 'failed', error_message = 'Agent heartbeat lost (Lease Expired)' WHERE id = $1`
				_, err = m.db.Exec(ctx, updateQuery, taskID)
				if err != nil {
					log.Error("lease_monitor: failed to mark task as failed", zap.Error(err))
					continue
				}
				
				// Optional: Set project to failed if a task permanently fails
				if _, err := m.db.Exec(ctx, `UPDATE projects SET status = 'failed' WHERE id = $1`, projectID); err != nil {
					log.Error("lease_monitor: failed to mark project as failed", zap.Error(err))
				}
			}
		}
	}
}
