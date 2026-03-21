package server

import (
	"context"
	"encoding/json"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/kafka"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// ResultHandler processes task results from Kafka and advances the DAG.
type ResultHandler struct {
	db       *db.Pool
	redis    *db.Redis
	producer *kafka.Producer
	saga     *SagaCoordinator
}

func NewResultHandler(pool *db.Pool, rds *db.Redis, prod *kafka.Producer, saga *SagaCoordinator) *ResultHandler {
	return &ResultHandler{
		db:       pool,
		redis:    rds,
		producer: prod,
		saga:     saga,
	}
}

// ResultMessage matches the Python pydantic schema in messaging/schemas.py
type ResultMessage struct {
	TaskID       string         `json:"task_id"`
	ProjectID     string         `json:"project_id"`
	AgentRole     string         `json:"agent_role"`
	Status        string         `json:"status"` // completed | failed
	OutputData    map[string]any `json:"output_data"`
	ErrorMessage  string         `json:"error_message,omitempty"`
	DurationMS    int            `json:"duration_ms"`
	TraceID       string         `json:"trace_id"`
	CompletedAt   string         `json:"completed_at"`
	CostUSD       float64        `json:"cost_usd"`
	TokensUsed    int            `json:"tokens_used"`
	ModelUsed     string         `json:"model_used,omitempty"`
	Version       int            `json:"version"`
}

func (h *ResultHandler) Handle(ctx context.Context, msg kafka.Message) error {
	log := logger.L()

	var res ResultMessage
	if err := json.Unmarshal(msg.Value, &res); err != nil {
		log.Error("failed to unmarshal result message", zap.Error(err), zap.ByteString("payload", msg.Value))
		return err
	}

	// Register/initialize saga for this project if not present
	h.saga.RegisterSaga(res.ProjectID, res.OutputData)

	log.Info("processing result", 
		zap.String("project_id", res.ProjectID), 
		zap.String("task_id", res.TaskID), 
		zap.String("status", res.Status),
		zap.String("agent", res.AgentRole),
	)

	// 1. Update Task status in DB
	status := "done"
	if res.Status == "failed" {
		status = "failed"
	}

	updateQuery := `
		UPDATE tasks 
		SET status = $1, output_data = $2, error_message = $3, completed_at = $4, version = version + 1 
		WHERE id = $5 AND version = $6 AND status != 'done'`
	
	outJSON, _ := json.Marshal(res.OutputData)
	tag, err := h.db.Exec(ctx, updateQuery, status, outJSON, res.ErrorMessage, time.Now(), res.TaskID, res.Version)
	if err != nil {
		log.Error("failed to update task status in db", zap.Error(err))
		return err
	}

	if tag.RowsAffected() == 0 {
		log.Warn("idempotent update: task already processed or version mismatch", 
			zap.String("task_id", res.TaskID), zap.Int("version", res.Version))
		return nil // Return nil so we don't retry processing a duplicate
	}

	// 1.5 Clear the Redis lease as the task is no longer running
	_ = h.redis.ClearTaskLease(ctx, res.TaskID)

	// Record costs
	if res.ModelUsed != "" || res.TokensUsed > 0 || res.CostUSD > 0 {
		modelUsed := res.ModelUsed
		if modelUsed == "" {
			modelUsed = "unknown"
		}
		costQuery := `INSERT INTO cost_events (project_id, task_id, agent_role, model_used, tokens_in, cost_usd)
					  VALUES ($1, $2, $3, $4, $5, $6)`
		_, err = h.db.Exec(ctx, costQuery, res.ProjectID, res.TaskID, res.AgentRole, modelUsed, res.TokensUsed, res.CostUSD)
		if err != nil {
			log.Warn("failed to record cost_event", zap.Error(err))
		}
	}

	// 2. Logic to "Advance the DAG"
	// For this hackathon version, we hardcode the next step after CEO planning.
	// In the future, this would fetch the DAG and see what's ready.
	if res.AgentRole == "CEO" && status == "done" {
		return h.dispatchNextAfterCEO(ctx, res)
	}

	if res.AgentRole == "CTO" && status == "done" {
		return h.dispatchNext(ctx, res, "Engineer_Backend", "Backend Implementation", "code")
	}

	if res.AgentRole == "Engineer_Backend" && status == "done" {
		// Mark project as done after backend is built
		_, _ = h.db.Exec(ctx, `UPDATE projects SET status = 'done', completed_at = $1 WHERE id = $2`, time.Now(), res.ProjectID)
		return nil
	}

	// Advance the saga locally
	if status == "done" {
		h.saga.Advance(res.ProjectID, res.AgentRole)
	}

	if status == "failed" {
		log.Warn("step failed, triggering saga compensation", zap.String("agent", res.AgentRole))
		_ = h.saga.HandleFailure(ctx, res.ProjectID, res.AgentRole)
		_, _ = h.db.Exec(ctx, `UPDATE projects SET status = 'recovering' WHERE id = $1`, res.ProjectID)
		return nil
	}

	return nil
}

func (h *ResultHandler) dispatchNextAfterCEO(ctx context.Context, res ResultMessage) error {
	log := logger.L()

	// After CEO Planning -> CTO System Design
	taskID := uuid.NewString()
	taskQuery := `INSERT INTO tasks (id, project_id, name, task_type, agent_role, status)
				  VALUES ($1, $2, $3, $4, $5, 'pending')`
	_, err := h.db.Exec(ctx, taskQuery, taskID, res.ProjectID, "System Architecture Design", "design", "CTO")
	if err != nil {
		log.Error("failed to insert CTO task", zap.Error(err))
		return err
	}

	// Dispatch CTO task
	taskPayload := map[string]any{
		"task_id":    taskID,
		"task_name":  "System Architecture Design",
		"task_type":  "design",
		"agent_role": "CTO",
		"project_id": res.ProjectID,
		"trace_id":   res.TraceID,
		"input_data": map[string]any{
			"business_plan": res.OutputData,
			"llm_config": map[string]any{
				"provider": "bedrock",
				"model":    "amazon.nova-pro-v1:0",
			},
		},
	}

	_, _, err = h.producer.PublishJSON("ai-org-tasks", res.ProjectID, taskPayload)
	if err != nil {
		log.Error("failed to publish CTO task to kafka", zap.Error(err))
		return err
	}

	log.Info("DAG advanced: CEO -> CTO", zap.String("project_id", res.ProjectID))
	return nil
}

func (h *ResultHandler) dispatchNext(ctx context.Context, res ResultMessage, agentRole, taskName, taskType string) error {
	log := logger.L()

	taskID := uuid.NewString()
	taskQuery := `INSERT INTO tasks (id, project_id, name, task_type, agent_role, status)
				  VALUES ($1, $2, $3, $4, $5, 'pending')`
	_, err := h.db.Exec(ctx, taskQuery, taskID, res.ProjectID, taskName, taskType, agentRole)
	if err != nil {
		log.Error("failed to insert task", zap.Error(err))
		return err
	}

	taskPayload := map[string]any{
		"task_id":    taskID,
		"task_name":  taskName,
		"task_type":  taskType,
		"agent_role": agentRole,
		"project_id": res.ProjectID,
		"trace_id":   res.TraceID,
		"input_data": map[string]any{
			"architecture": res.OutputData,
			"llm_config": map[string]any{
				"provider": "bedrock",
				"model":    "amazon.nova-lite-v1:0", // Engineer model
			},
		},
	}

	_, _, err = h.producer.PublishJSON("ai-org-tasks", res.ProjectID, taskPayload)
	if err != nil {
		log.Error("failed to publish task to kafka", zap.Error(err))
		return err
	}

	log.Info("DAG advanced", zap.String("project_id", res.ProjectID), zap.String("next_agent", agentRole))
	return nil
}
