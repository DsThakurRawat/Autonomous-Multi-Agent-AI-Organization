// tasks_handler.go — Task and event read endpoints
//
// Routes (registered in cmd/gateway/main.go):
//
//	GET /v1/projects/:id/tasks   — DAG task list for the DagViewer component
//	GET /v1/projects/:id/events  — Recent event log for the AgentFeed component
package handler

import (
	"context"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// TasksHandler handles task and event read routes.
type TasksHandler struct {
	db *db.Pool
}

func NewTasksHandler(pool *db.Pool) *TasksHandler {
	return &TasksHandler{db: pool}
}

// ── Types ─────────────────────────────────────────────────────────────────────

// TaskNode is the read model returned for each DAG task.
// Matches the TaskNode interface in dashboard/lib/api.ts.
type TaskNode struct {
	ID          string     `json:"id"`
	Name        string     `json:"name"`
	AgentRole   string     `json:"agent_role"`
	TaskType    string     `json:"task_type"`
	Status      string     `json:"status"`
	DependsOn   []string   `json:"depends_on"`
	DurationMs  *int       `json:"duration_ms,omitempty"`
	StartedAt   *time.Time `json:"started_at,omitempty"`
	CompletedAt *time.Time `json:"completed_at,omitempty"`
	ErrorMsg    string     `json:"error_msg,omitempty"`
}

// EventEntry is a single event from the agent_events table.
type EventEntry struct {
	ID        string    `json:"id"`
	AgentRole string    `json:"agent_role"`
	EventType string    `json:"event_type"`
	Message   string    `json:"message"`
	Level     string    `json:"level"`
	TraceID   string    `json:"trace_id,omitempty"`
	CreatedAt time.Time `json:"created_at"`
}

// ── Handlers ──────────────────────────────────────────────────────────────────

// GetProjectTasks handles GET /v1/projects/:id/tasks
// Returns the full DAG for the selected project, including dependency edges.
func (h *TasksHandler) GetProjectTasks(c *fiber.Ctx) error {
	projectID := c.Params("id")
	log := logger.L().With(zap.String("project_id", projectID))

	// Fetch all tasks for this project
	rows, err := h.db.Query(context.Background(), `
		SELECT
			t.id, t.name, t.agent_role, t.task_type, t.status,
			t.duration_ms, t.started_at, t.completed_at,
			COALESCE(t.error_msg, '') AS error_msg
		FROM tasks t
		WHERE t.project_id = $1
		ORDER BY t.created_at ASC`,
		projectID,
	)
	if err != nil {
		log.Error("GetProjectTasks query failed", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: err.Error()})
	}
	defer rows.Close()

	taskMap := map[string]*TaskNode{}
	var order []string

	for rows.Next() {
		var t TaskNode
		if err := rows.Scan(
			&t.ID, &t.Name, &t.AgentRole, &t.TaskType, &t.Status,
			&t.DurationMs, &t.StartedAt, &t.CompletedAt, &t.ErrorMsg,
		); err != nil {
			continue
		}
		t.DependsOn = []string{}
		taskMap[t.ID] = &t
		order = append(order, t.ID)
	}

	// Fetch dependency edges
	depRows, err := h.db.Query(context.Background(), `
		SELECT task_id::text, depends_on::text
		FROM task_dependencies
		WHERE task_id IN (
			SELECT id FROM tasks WHERE project_id = $1
		)`,
		projectID,
	)
	if err == nil {
		defer depRows.Close()
		for depRows.Next() {
			var taskID, depID string
			if err := depRows.Scan(&taskID, &depID); err != nil {
				continue
			}
			if t, ok := taskMap[taskID]; ok {
				t.DependsOn = append(t.DependsOn, depID)
			}
		}
	}

	// Return in creation order
	result := make([]TaskNode, 0, len(order))
	for _, id := range order {
		if t, ok := taskMap[id]; ok {
			result = append(result, *t)
		}
	}

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"project_id": projectID,
		"tasks":      result,
		"total":      len(result),
	})
}

// GetProjectEvents handles GET /v1/projects/:id/events
// Returns recent 200 events for the AgentFeed component.
// The real-time stream is handled by the ws-hub WebSocket service.
func (h *TasksHandler) GetProjectEvents(c *fiber.Ctx) error {
	projectID := c.Params("id")

	rows, err := h.db.Query(context.Background(), `
		SELECT
			id::text, agent_role, event_type, message, level,
			COALESCE(trace_id::text, '') AS trace_id,
			created_at
		FROM agent_events
		WHERE project_id = $1
		ORDER BY created_at DESC
		LIMIT 200`,
		projectID,
	)
	if err != nil {
		// agent_events may not exist yet — return empty gracefully
		return c.Status(fiber.StatusOK).JSON(fiber.Map{"events": []any{}, "total": 0})
	}
	defer rows.Close()

	var events []EventEntry
	for rows.Next() {
		var e EventEntry
		if err := rows.Scan(
			&e.ID, &e.AgentRole, &e.EventType, &e.Message, &e.Level,
			&e.TraceID, &e.CreatedAt,
		); err != nil {
			continue
		}
		events = append(events, e)
	}
	if events == nil {
		events = []EventEntry{}
	}

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"project_id": projectID,
		"events":     events,
		"total":      len(events),
	})
}
