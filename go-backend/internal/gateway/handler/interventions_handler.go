package handler

import (
	"context"
	"encoding/json"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	redisclient "github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/redis"
)

type InterventionsHandler struct {
	redis *redisclient.Client
}

func NewInterventionsHandler(rdb *redisclient.Client) *InterventionsHandler {
	return &InterventionsHandler{redis: rdb}
}

type InterventionRequest struct {
	Approved bool `json:"approved"`
}

func (h *InterventionsHandler) PostIntervention(c *fiber.Ctx) error {
	projectID := c.Params("id")
	taskID := c.Params("task_id")
	log := logger.L().With(zap.String("project_id", projectID), zap.String("task_id", taskID))

	var req InterventionRequest
	if err := c.BodyParser(&req); err != nil {
		return c.Status(fiber.StatusBadRequest).JSON(ErrorResponse{Code: 400, Error: "Invalid request body"})
	}

	interventionID := "intervention:" + taskID
	payload, _ := json.Marshal(map[string]bool{"approved": req.Approved})

	// Publish to Redis Pub/Sub so the blocked Python Agent unlocks immediately
	if err := h.redis.Publish(context.Background(), interventionID, string(payload)); err != nil {
		log.Error("Failed to publish intervention to Redis", zap.Error(err))
		return c.Status(fiber.StatusInternalServerError).JSON(ErrorResponse{Code: 500, Error: "Internal backend error"})
	}

	log.Info("Human intervention published", zap.Bool("approved", req.Approved))

	return c.Status(fiber.StatusOK).JSON(fiber.Map{
		"status":   "success",
		"approved": req.Approved,
	})
}
