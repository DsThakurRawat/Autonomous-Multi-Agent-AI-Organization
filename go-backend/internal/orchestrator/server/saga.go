package server

import (
	"context"
	"fmt"
	"sync"
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
	producer *kafka.Producer
	sagas    map[string]*SagaState // In-memory for now, should be in DB/Redis for multi-node
	mu       sync.RWMutex
}

func NewSagaCoordinator(pool *db.Pool, prod *kafka.Producer) *SagaCoordinator {
	return &SagaCoordinator{
		db:       pool,
		producer: prod,
		sagas:    make(map[string]*SagaState),
	}
}

// RegisterSaga starts or resumes a saga for a project.
func (sc *SagaCoordinator) RegisterSaga(projectID string, initialPayload map[string]any) {
	sc.mu.Lock()
	defer sc.mu.Unlock()
	
	if _, exists := sc.sagas[projectID]; !exists {
		sc.sagas[projectID] = &SagaState{
			ProjectID:   projectID,
			CurrentStep: 0,
			Payload:     initialPayload,
			Status:      "forward",
		}
	}
}

// HandleFailure triggers compensation logic if a step fails.
func (sc *SagaCoordinator) HandleFailure(ctx context.Context, projectID string, failedAgent string) error {
	log := logger.L()
	sc.mu.Lock()
	state, exists := sc.sagas[projectID]
	sc.mu.Unlock()

	if !exists {
		return fmt.Errorf("no active saga found for project %s", projectID)
	}

	log.Warn("Saga failure detected, initiating compensation", 
		zap.String("project_id", projectID), 
		zap.String("failed_agent", failedAgent),
	)

	state.Status = "compensating"
	
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

	_, _, err := sc.producer.PublishJSON("ai-org-tasks", projectID, taskPayload)
	return err
}

// Advance records a successful step and prepares for the next.
func (sc *SagaCoordinator) Advance(projectID string, agentRole string) {
	sc.mu.Lock()
	defer sc.mu.Unlock()
	
	if state, ok := sc.sagas[projectID]; ok {
		state.History = append(state.History, fmt.Sprintf("%s_completed_at_%s", agentRole, time.Now().Format(time.RFC3339)))
		state.CurrentStep++
	}
}
