package server

import (
	"context"
	"encoding/json"
	"time"

	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/kafka"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// HeartbeatHandler processes agent heartbeats and extends leases.
type HeartbeatHandler struct {
	redis *db.Redis
}

func NewHeartbeatHandler(rds *db.Redis) *HeartbeatHandler {
	return &HeartbeatHandler{
		redis: rds,
	}
}

// HeartbeatMessage matches the expected schema from Python agents.
type HeartbeatMessage struct {
	TaskID    string `json:"task_id"`
	Timestamp string `json:"timestamp"`
	Progress  string `json:"progress,omitempty"`
}

func (h *HeartbeatHandler) Handle(ctx context.Context, msg kafka.Message) error {
	log := logger.L()

	var hb HeartbeatMessage
	if err := json.Unmarshal(msg.Value, &hb); err != nil {
		log.Error("failed to unmarshal heartbeat", zap.Error(err))
		return err
	}

	// Extend the lease in Redis by another 30s
	// This ensures that as long as the agent is alive and pulsing, the lease doesn't expire.
	_, err := h.redis.SetTaskLease(ctx, hb.TaskID, 30*time.Second)
	if err != nil {
		log.Error("failed to extend task lease on heartbeat", zap.String("task_id", hb.TaskID), zap.Error(err))
		return err
	}

	log.Debug("task lease extended", zap.String("task_id", hb.TaskID), zap.String("progress", hb.Progress))
	return nil
}
