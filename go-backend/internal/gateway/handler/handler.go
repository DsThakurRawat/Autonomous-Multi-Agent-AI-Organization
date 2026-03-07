package handler

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/gateway/grpcclient"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	pb "github.com/DsThakurRawat/autonomous-org/go-backend/proto/gen/orchestrator"
)

// Handler holds the dependencies mapped to HTTP routes
type Handler struct {
	OrchClient *grpcclient.OrchestratorClient
	db         *db.Pool
}

func NewHandler(orchClient *grpcclient.OrchestratorClient, pool *db.Pool) *Handler {
	return &Handler{
		OrchClient: orchClient,
		db:         pool,
	}
}

// ── Request/Response types ────────────────────────────────────────────────────

type CreateProjectRequest struct {
	Idea   string      `json:"idea"   validate:"required,min=10,max=2000"`
	Budget BudgetInput `json:"budget"`
}

type BudgetInput struct {
	MaxCostUSD float64 `json:"max_cost_usd"`
	MaxTokens  int64   `json:"max_tokens"`
}

type ProjectResponse struct {
	ProjectID string    `json:"project_id"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
	Message   string    `json:"message,omitempty"`
}

// ProjectListItem is the read model returned by ListProjects
type ProjectListItem struct {
	ID          string     `json:"id"`
	Idea        string     `json:"idea"`
	Status      string     `json:"status"`
	BudgetUSD   float64    `json:"budget_usd"`
	SpentUSD    float64    `json:"spent_usd"`
	ProgressPct int        `json:"progress_pct"`
	TasksTotal  int        `json:"tasks_total"`
	TasksDone   int        `json:"tasks_done"`
	CreatedAt   time.Time  `json:"created_at"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
}

type ErrorResponse struct {
	Code    int    `json:"code"`
	Error   string `json:"error"`
	TraceID string `json:"trace_id,omitempty"`
}

// ── Handlers ──────────────────────────────────────────────────────────────────

// CreateProject handles POST /v1/projects
func (h *Handler) CreateProject(c *fiber.Ctx) error {
	log := logger.L().With(
		zap.String("handler", "CreateProject"),
		zap.String("trace_id", traceID(c)),
	)

	var req CreateProjectRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
			Code:    400,
			Error:   "invalid request body: " + err.Error(),
			TraceID: traceID(c),
		})
	}

	if len(req.Idea) < 10 {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{
			Code:  400,
			Error: "idea must be at least 10 characters",
		})
	}

	userID, _ := c.Locals("user_id").(string)
	tenantID, _ := c.Locals("tenant_id").(string)

	resp, err := h.OrchClient.CreateProject(context.Background(), &pb.CreateProjectRequest{
		TenantId: tenantID,
		UserId:   userID,
		Idea:     req.Idea,
		Budget: &pb.BudgetConfig{
			MaxCostUsd: req.Budget.MaxCostUSD,
			MaxTokens:  req.Budget.MaxTokens,
		},
	})

	if err != nil {
		log.Error("failed to create project via gRPC", zap.Error(err))
		return c.Status(fiber.StatusServiceUnavailable).JSON(ErrorResponse{
			Code:    503,
			Error:   "orchestrator unavailable: please try again later",
			TraceID: traceID(c),
		})
	}

	return c.Status(fiber.StatusAccepted).JSON(ProjectResponse{
		ProjectID: resp.GetProjectId(),
		Status:    resp.GetStatus().String(),
		CreatedAt: resp.GetCreatedAt().AsTime(),
		Message:   "Project queued. Connect to /v1/projects/" + resp.GetProjectId() + "/stream for live updates.",
	})
}

// ListProjects handles GET /v1/projects
// Returns all projects for the authenticated user with aggregated task counts.
func (h *Handler) ListProjects(c *fiber.Ctx) error {
	userID, _ := c.Locals("user_id").(string)
	if userID == "" {
		return c.Status(fiber.StatusOK).JSON(fiber.Map{"projects": []any{}, "total": 0})
	}

	rows, err := h.db.Query(context.Background(), `
		SELECT
			p.id,
			p.idea,
			CASE 
				WHEN p.status = 'active' THEN 'processing'
				WHEN p.status = 'done' THEN 'completed'
				ELSE p.status 
			END AS status,
			COALESCE(p.budget_usd, 0)                                                 AS budget_usd,
			COALESCE((SELECT SUM(cost_usd) FROM cost_events ce WHERE ce.project_id = p.id), 0) AS spent_usd,
			COUNT(t.id)                                                               AS tasks_total,
			COUNT(t.id) FILTER (WHERE t.status = 'done')                              AS tasks_done,
			p.created_at,
			p.completed_at
		FROM projects p
		LEFT JOIN tasks t ON t.project_id = p.id
		WHERE p.user_id = $1
		GROUP BY p.id
		ORDER BY p.created_at DESC
		LIMIT 100`,
		userID,
	)
	if err != nil {
		logger.L().Error("ListProjects query failed", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: err.Error()})
	}
	defer rows.Close()

	var projects []ProjectListItem
	for rows.Next() {
		var p ProjectListItem
		if err := rows.Scan(
			&p.ID, &p.Idea, &p.Status,
			&p.BudgetUSD, &p.SpentUSD,
			&p.TasksTotal, &p.TasksDone,
			&p.CreatedAt, &p.CompletedAt,
		); err != nil {
			continue
		}
		// Compute progress
		if p.TasksTotal > 0 {
			p.ProgressPct = int(float64(p.TasksDone) / float64(p.TasksTotal) * 100)
		}
		projects = append(projects, p)
	}
	if projects == nil {
		projects = []ProjectListItem{}
	}

	return c.Status(fiber.StatusOK).JSON(fiber.Map{"projects": projects, "total": len(projects)})
}

// GetProject handles GET /v1/projects/:id
// First tries the Orchestrator gRPC stub, falls back to direct DB read.
func (h *Handler) GetProject(c *fiber.Ctx) error {
	projectID := c.Params("id")
	userID, _ := c.Locals("user_id").(string)

	if projectID == "" {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Code: 400, Error: "project_id required"})
	}

	// Direct DB read — Orchestrator stub only returns hardcoded data for now
	var p ProjectListItem
	err := h.db.QueryRow(context.Background(), `
		SELECT
			p.id, p.idea, 
			CASE 
				WHEN p.status = 'active' THEN 'processing'
				WHEN p.status = 'done' THEN 'completed'
				ELSE p.status 
			END AS status,
			COALESCE(p.budget_usd, 0) AS budget_usd,
			COALESCE((SELECT SUM(cost_usd) FROM cost_events ce WHERE ce.project_id = p.id), 0) AS spent_usd,
			COUNT(t.id) AS tasks_total,
			COUNT(t.id) FILTER (WHERE t.status = 'done') AS tasks_done,
			p.created_at, p.completed_at
		FROM projects p
		LEFT JOIN tasks t ON t.project_id = p.id
		WHERE p.id = $1 AND p.user_id = $2
		GROUP BY p.id`,
		projectID, userID,
	).Scan(
		&p.ID, &p.Idea, &p.Status,
		&p.BudgetUSD, &p.SpentUSD,
		&p.TasksTotal, &p.TasksDone,
		&p.CreatedAt, &p.CompletedAt,
	)

	if err != nil {
		return c.Status(fiber.StatusNotFound).JSON(ErrorResponse{Code: 404, Error: "project not found"})
	}

	if p.TasksTotal > 0 {
		p.ProgressPct = int(float64(p.TasksDone) / float64(p.TasksTotal) * 100)
	}

	return c.Status(fiber.StatusOK).JSON(p)
}

// CancelProject handles DELETE /v1/projects/:id
func (h *Handler) CancelProject(c *fiber.Ctx) error {
	projectID := c.Params("id")

	resp, err := h.OrchClient.CancelProject(context.Background(), &pb.CancelProjectRequest{
		ProjectId: projectID,
		Reason:    "Requested via API",
	})

	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: err.Error()})
	}

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"success":    resp.GetSuccess(),
		"message":    resp.GetMessage(),
		"project_id": projectID,
	})
}

// GetCostReport handles GET /v1/projects/:id/cost
// Returns total spend + per-agent breakdown from cost_events table.
func (h *Handler) GetCostReport(c *fiber.Ctx) error {
	projectID := c.Params("id")

	// Per-agent aggregation
	rows, err := h.db.Query(context.Background(), `
		SELECT
			agent_role,
			COALESCE(SUM(cost_usd), 0)   AS cost_usd,
			COALESCE(SUM(tokens_in), 0)  AS tokens_in,
			COALESCE(SUM(tokens_out), 0) AS tokens_out,
			COUNT(*)                     AS calls
		FROM cost_events
		WHERE project_id = $1
		GROUP BY agent_role
		ORDER BY cost_usd DESC`,
		projectID,
	)
	if err != nil {
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: err.Error()})
	}
	defer rows.Close()

	type agentCost struct {
		Role      string  `json:"agent_role"`
		CostUSD   float64 `json:"cost_usd"`
		TokensIn  int64   `json:"tokens_in"`
		TokensOut int64   `json:"tokens_out"`
		Calls     int     `json:"calls"`
	}

	var byAgent []agentCost
	var totalUSD float64
	for rows.Next() {
		var a agentCost
		if err := rows.Scan(&a.Role, &a.CostUSD, &a.TokensIn, &a.TokensOut, &a.Calls); err != nil {
			continue
		}
		totalUSD += a.CostUSD
		byAgent = append(byAgent, a)
	}
	if byAgent == nil {
		byAgent = []agentCost{}
	}

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"project_id": projectID,
		"total_usd":  totalUSD,
		"by_agent":   byAgent,
	})
}

// HealthCheck handles GET /healthz
func (h *Handler) HealthCheck(c *fiber.Ctx) error {
	return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "ok", "ts": time.Now().Unix()})
}

// ReadyCheck handles GET /readyz
func (h *Handler) ReadyCheck(c *fiber.Ctx) error {
	return c.Status(fiber.StatusOK).JSON(fiber.Map{"status": "ready"})
}

// traceID extracts the trace_id local or returns empty string safely.
func traceID(c *fiber.Ctx) string {
	v, _ := c.Locals("trace_id").(string)
	return v
}
