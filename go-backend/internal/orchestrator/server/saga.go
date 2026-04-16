package server

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/kafka"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	"github.com/google/uuid"
	"go.uber.org/zap"
)

// SagaStep defines a single step in a distributed transaction.
type SagaStep struct {
	Name            string
	AgentRole       string
	TaskType        string
	Action          func(ctx context.Context, projectID string, input map[string]any) error
	Compensate      func(ctx context.Context, projectID string, input map[string]any) error
}

// SagaState tracks the progress of a Saga instance.
type SagaState struct {
	ProjectID   string
	CurrentStep int
	History     []string
	Payload     map[string]any
	Status      string // "forward", "compensating", "completed", "failed"
}

// SagaCoordinator manages the execution of Sagas.
type SagaCoordinator struct {
	db       *db.Pool
	redis    *db.Redis
	producer *kafka.Producer
}

func NewSagaCoordinator(pool *db.Pool, rds *db.Redis, prod *kafka.Producer) *SagaCoordinator {
	return &SagaCoordinator{
		db:       pool,
		redis:    rds,
		producer: prod,
	}
}

// RegisterSaga starts or resumes a saga for a project.
func (sc *SagaCoordinator) RegisterSaga(ctx context.Context, projectID string, initialPayload map[string]any) {
	key := fmt.Sprintf("saga:state:%s", projectID)
	
	// Check if already exists in Redis
	exists, _ := sc.redis.Client.Exists(ctx, key).Result()
	if exists > 0 {
		return
	}

	state := &SagaState{
		ProjectID:   projectID,
		CurrentStep: 0,
		Payload:     initialPayload,
		Status:      "forward",
	}

	data, _ := json.Marshal(state)
	sc.redis.Client.Set(ctx, key, data, 24*time.Hour)
}

// HandleFailure triggers compensation logic if a step fails.
func (sc *SagaCoordinator) HandleFailure(ctx context.Context, projectID string, failedAgent string) error {
	log := logger.L()
	key := fmt.Sprintf("saga:state:%s", projectID)

	val, err := sc.redis.Client.Get(ctx, key).Result()
	if err != nil {
		return fmt.Errorf("no active saga found in redis for project %s", projectID)
	}

	var state SagaState
	if err := json.Unmarshal([]byte(val), &state); err != nil {
		return err
	}

	log.Warn("Saga failure detected, initiating compensation", 
		zap.String("project_id", projectID), 
		zap.String("failed_agent", failedAgent),
	)

	state.Status = "compensating"
	data, _ := json.Marshal(&state)
	sc.redis.Client.Set(ctx, key, data, 24*time.Hour)
	
	// Implementation note: In a real distributed system, we would:
	// 1. Identify all completed steps in reverse order.
	// 2. Dispatch "Undo" tasks to agents to clean up (e.g., delete temp files, revert DB).
	
	// For this phase, we append a "Correction" task back to the CTO or CEO
	// to re-evaluate the plan instead of just failing the project.
	
	correctionTaskID := uuid.NewString()
	msg := fmt.Sprintf("Recovery: Previous step by %s failed. Please re-adjust strategy.", failedAgent)
	
	taskPayload := map[string]any{
		"task_id":      correctionTaskID,
		"task_name":    "Strategic Recovery & Compensation",
		"task_type":    "strategy",
		"agent_role":   "CEO", // Fallback to CEO for strategic correction
		"project_id":   projectID,
		"input_data": map[string]any{
			"error_context": msg,
			"saga_history":  state.History,
		},
	}

	_, _, err = sc.producer.PublishJSON("ai-org-tasks", projectID, taskPayload)
	return err
}

// Advance records a successful step and prepares for the next.
func (sc *SagaCoordinator) Advance(ctx context.Context, projectID string, agentRole string) {
	key := fmt.Sprintf("saga:state:%s", projectID)

	val, err := sc.redis.Client.Get(ctx, key).Result()
	if err != nil {
		return
	}

	var state SagaState
	if err := json.Unmarshal([]byte(val), &state); err != nil {
		return
	}

	state.History = append(state.History, fmt.Sprintf("%s_completed_at_%s", agentRole, time.Now().Format(time.RFC3339)))
	state.CurrentStep++

	data, _ := json.Marshal(&state)
	sc.redis.Client.Set(ctx, key, data, 24*time.Hour)
}
