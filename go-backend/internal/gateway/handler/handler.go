// Package handler implements the HTTP REST handlers for the API Gateway.
// All handlers are pure functions — dependencies injected via closure.
package handler

import (
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// ── Request/Response types ────────────────────────────────────────────────────

type CreateProjectRequest struct {
	Idea   string      `json:"idea" validate:"required,min=10,max=2000"`
	Budget BudgetInput `json:"budget"`
}

type BudgetInput struct {
	MaxCostUSD float64 `json:"max_cost_usd"` // 0 = use tenant default
	MaxTokens  int64   `json:"max_tokens"`
}

type ProjectResponse struct {
	ProjectID string    `json:"project_id"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
	Message   string    `json:"message,omitempty"`
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Error   string `json:"error"`
	TraceID string `json:"trace_id,omitempty"`
}

// ── Handlers ──────────────────────────────────────────────────────────────────

// CreateProject handles POST /v1/projects
// Validates the request, creates a project record, and submits to the orchestrator.
func CreateProject(c *fiber.Ctx) error {
	log := logger.L().With(
		zap.String("handler", "CreateProject"),
		zap.String("trace_id", c.Locals("trace_id").(string)),
	)

	var req CreateProjectRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
			Code:    400,
			Error:   "invalid request body: " + err.Error(),
			TraceID: c.Locals("trace_id").(string),
		})
	}

	// Validate
	if len(req.Idea) < 10 {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
			Code:  400,
			Error: "idea must be at least 10 characters",
		})
	}

	// Get user context injected by JWT middleware
	userID, _ := c.Locals("user_id").(string)
	tenantID, _ := c.Locals("tenant_id").(string)

	projectID := uuid.NewString()

	log.Info("project creation request",
		zap.String("project_id", projectID),
		zap.String("user_id", userID),
		zap.String("tenant_id", tenantID),
		zap.String("idea_preview", req.Idea[:min(len(req.Idea), 60)]),
	)

	// TODO: call orchestrator gRPC service
	// resp, err := orchestratorClient.CreateProject(c.Context(), &pb.CreateProjectRequest{...})

	return c.Status(fiber.StatusAccepted).JSON(ProjectResponse{
		ProjectID: projectID,
		Status:    "pending",
		CreatedAt: time.Now().UTC(),
		Message:   "Project queued. Connect to /v1/projects/" + projectID + "/stream for live updates.",
	})
}

// GetProject handles GET /v1/projects/:id
func GetProject(c *fiber.Ctx) error {
	projectID := c.Params("id")
	tenantID, _ := c.Locals("tenant_id").(string)

	if projectID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Code: 400, Error: "project_id required"})
	}

	logger.L().Info("get project", zap.String("project_id", projectID), zap.String("tenant_id", tenantID))

	// TODO: call orchestrator gRPC GetProject
	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"project_id": projectID,
		"status":     "running",
		"tenant_id":  tenantID,
	})
}

// ListProjects handles GET /v1/projects
func ListProjects(c *fiber.Ctx) error {
	tenantID, _ := c.Locals("tenant_id").(string)
	userID, _ := c.Locals("user_id").(string)

	logger.L().Info("list projects", zap.String("user_id", userID), zap.String("tenant_id", tenantID))

	// TODO: query postgres with tenant_id filter
	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"projects": []any{},
		"total":    0,
	})
}

// CancelProject handles DELETE /v1/projects/:id
func CancelProject(c *fiber.Ctx) error {
	projectID := c.Params("id")
	logger.L().Info("cancel project", zap.String("project_id", projectID))
	// TODO: call orchestrator gRPC CancelProject
	return c.Status(fiber.StatusOK).JSON(fiber.Map{"message": "cancellation requested", "project_id": projectID})
}

// GetCostReport handles GET /v1/projects/:id/cost
func GetCostReport(c *fiber.Ctx) error {
	projectID := c.Params("id")
	// TODO: query cost_events table
	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"project_id":     projectID,
		"total_cost_usd": 0.0,
		"total_tokens":   0,
	})
}

// HealthCheck handles GET /healthz — liveness probe
func HealthCheck(c *fiber.Ctx) error {
	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":  "ok",
		"service": "gateway",
		"time":    time.Now().UTC(),
	})
}

// ReadyCheck handles GET /readyz — readiness probe
func ReadyCheck(c *fiber.Ctx) error {
	// TODO: check DB and Redis connectivity
	return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "ready"})
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
