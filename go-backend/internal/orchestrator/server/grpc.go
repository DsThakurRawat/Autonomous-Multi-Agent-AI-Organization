package server

import (
	"context"
	"time"

	"github.com/google/uuid"
	"go.uber.org/zap"
	"google.golang.org/protobuf/types/known/timestamppb"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/kafka"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/keystore"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	pb "github.com/DsThakurRawat/autonomous-org/go-backend/proto/gen/orchestrator"
)

// OrchestratorServer implements the gRPC OrchestratorServiceServer
type OrchestratorServer struct {
	pb.UnimplementedOrchestratorServiceServer

	db       *db.Pool
	redis    *db.Redis
	producer *kafka.Producer
	keys     *keystore.Resolver // resolves per-user LLM config at dispatch time
}

func NewOrchestratorServer(pool *db.Pool, rds *db.Redis, prod *kafka.Producer) *OrchestratorServer {
	return &OrchestratorServer{
		db:       pool,
		redis:    rds,
		producer: prod,
		keys:     keystore.NewResolver(pool),
	}
}

func (s *OrchestratorServer) CreateProject(ctx context.Context, req *pb.CreateProjectRequest) (*pb.ProjectResponse, error) {
	log := logger.L().With(
		zap.String("user_id", req.GetUserId()),
		zap.String("tenant_id", req.GetTenantId()),
	)

	projectID := uuid.NewString()

	// Initialize the DAG for planning
	// Here we just insert the initial DB row for the Project,
	// and emit an event to Kafka so the Python Planning Agent picks it up.

	query := `INSERT INTO projects (id, tenant_id, user_id, idea, status, budget_usd) 
              VALUES ($1, $2, $3, $4, 'planning', $5)`

	// For now, assume budget max_cost_usd is set
	budget := req.GetBudget().GetMaxCostUsd()
	if budget == 0 {
		budget = 10.0 // Default 10 USD
	}

	_, err := s.db.Exec(ctx, query, projectID, req.GetTenantId(), req.GetUserId(), req.GetIdea(), budget)
	if err != nil {
		log.Error("failed to insert project", zap.Error(err))
		return nil, err
	}

	// Create initial Planning task
	taskID := uuid.NewString()
	taskQuery := `INSERT INTO tasks (id, project_id, name, task_type, agent_role, status)
				  VALUES ($1, $2, $3, $4, $5, 'pending')`
	_, err = s.db.Exec(ctx, taskQuery, taskID, projectID, "Requirement Analysis", "plan", "CEO")
	if err != nil {
		log.Error("failed to insert planning task", zap.Error(err))
		return nil, err
	}

	// Resolve the LLM config for this user+role before dispatching.
	// This is where the per-user API key is decrypted in memory and packed
	// into the Kafka message — the Python agent reads it from input_data.llm_config.
	llmCfg := s.keys.ResolveForAgent(ctx, req.GetUserId(), "CEO")
	llmConfigPayload := map[string]any{
		"provider": llmCfg.Provider,
		"api_key":  llmCfg.APIKey, // plaintext in RAM only, serialised to Kafka TLS channel
		"model":    llmCfg.ModelName,
	}

	// Check for existing lease in Redis to prevent duplicate dispatch
	leased, err := s.redis.IsTaskLeased(ctx, taskID)
	if err != nil {
		log.Warn("failed to check redis lease", zap.Error(err))
	}
	if leased {
		log.Info("task already leased, skipping duplicate dispatch", zap.String("task_id", taskID))
		return &pb.ProjectResponse{
			ProjectId: projectID,
			// ... return existing project info
		}, nil
	}

	// Set initial lease
	_, _ = s.redis.SetTaskLease(ctx, taskID, 30*time.Second)

	// Dispatch task to Kafka
	taskPayload := map[string]any{
		"task_id":    taskID,
		"task_name":  "Requirement Analysis",
		"task_type":  "plan",
		"agent_role": "CEO",
		"project_id": projectID,
		"trace_id":   uuid.NewString(),
		"input_data": map[string]any{
			"idea":       req.GetIdea(),
			"budget_usd": budget,
			"llm_config": llmConfigPayload,
		},
	}

	_, _, err = s.producer.PublishJSON("ai-org-tasks", projectID, taskPayload)
	if err != nil {
		log.Error("failed to publish task to kafka", zap.Error(err))
		return nil, err
	}

	log.Info("project created and planning task dispatched", zap.String("project_id", projectID))

	return &pb.ProjectResponse{
		ProjectId: projectID,
		TenantId:  req.GetTenantId(),
		UserId:    req.GetUserId(),
		Idea:      req.GetIdea(),
		Status:    pb.ProjectStatus_PROJECT_STATUS_PLANNING,
		CreatedAt: timestamppb.New(time.Now()),
	}, nil
}

func (s *OrchestratorServer) GetProject(ctx context.Context, req *pb.GetProjectRequest) (*pb.ProjectResponse, error) {
	// Simple lookup (Implementation deferred to fully connect the read paths)
	return &pb.ProjectResponse{
		ProjectId: req.GetProjectId(),
		TenantId:  req.GetTenantId(),
		Status:    pb.ProjectStatus_PROJECT_STATUS_RUNNING, // Hardcoded for stub
	}, nil
}

func (s *OrchestratorServer) StreamEvents(req *pb.StreamEventsRequest, stream pb.OrchestratorService_StreamEventsServer) error {
	// In the real system, Gateway connects via Websocket to ws-hub which handles fan-out.
	// This gRPC stream endpoint can be used for backend-to-backend streaming if needed.
	return nil
}

func (s *OrchestratorServer) CancelProject(ctx context.Context, req *pb.CancelProjectRequest) (*pb.StatusResponse, error) {
	// Simple stub for project cancellation
	query := `UPDATE projects SET status = 'cancelled' WHERE id = $1 AND status IN ('pending', 'planning', 'running')`
	res, err := s.db.Exec(ctx, query, req.GetProjectId())
	if err != nil {
		return nil, err
	}

	if res.RowsAffected() == 0 {
		return &pb.StatusResponse{Success: false, Message: "Project not found or cannot be cancelled"}, nil
	}

	// Cancel all pending or running tasks
	taskQuery := `UPDATE tasks SET status = 'skipped' WHERE project_id = $1 AND status IN ('pending', 'running')`
	_, _ = s.db.Exec(ctx, taskQuery, req.GetProjectId())

	// Emit cancellation event
	cancelEvent := map[string]any{
		"event_type": "project_cancelled",
		"project_id": req.GetProjectId(),
		"reason":     req.GetReason(),
	}
	_, _, _ = s.producer.PublishJSON("ai-org-events", req.GetProjectId(), cancelEvent)

	return &pb.StatusResponse{Success: true, Message: "Project cancelled"}, nil
}

func (s *OrchestratorServer) RetryTask(ctx context.Context, req *pb.RetryTaskRequest) (*pb.StatusResponse, error) {
	// Re-queue logic would go here
	// E.g., fetch DAG, g.MarkFailed(req.TaskId), if shouldRetry -> dispatcher
	return &pb.StatusResponse{Success: true, Message: "Task retry queued"}, nil
}

// Ensure interface compliance
var _ pb.OrchestratorServiceServer = (*OrchestratorServer)(nil)
