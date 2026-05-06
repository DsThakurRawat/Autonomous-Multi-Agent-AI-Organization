package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"os"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"go.uber.org/zap"
)

// -- Modern Data Models (Go Structs with Validation) -----------------

type ResearchMission struct {
	ID          string    `json:"id" binding:"required"`
	Name        string    `json:"name" binding:"required"`
	Goal        string    `json:"goal" binding:"required"`
	Status      string    `json:"status"`
	ProgressPct int       `json:"progress_pct"`
	CreatedAt   time.Time `json:"created_at"`
}

type AgentEvent struct {
	Type    string      `json:"type"`
	Message string      `json:"message"`
	Agent   string      `json:"agent"`
	Data    interface{} `json:"data,omitempty"`
}

type ChatMessage struct {
	MissionID string `json:"mission_id"`
	Message   string `json:"message" binding:"required"`
	AgentRole string `json:"agent_role"`
}

var (
	logger   *zap.Logger
	rdb      *redis.Client
	ctx      = context.Background()
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}
)

func init() {
	// Initialize Zap Logger
	var err error
	if os.Getenv("PROD") == "true" {
		logger, err = zap.NewProduction()
	} else {
		logger, err = zap.NewDevelopment()
	}
	if err != nil {
		panic(err)
	}

	// Initialize Redis for Dynamic Event Streaming
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "localhost:6379"
	}
	rdb = redis.NewClient(&redis.Options{
		Addr: redisURL,
	})
}

func main() {
	defer logger.Sync()
	r := gin.New()

	r.Use(gin.Recovery())
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000"},
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "SARANG Gateway Online", "redis_connected": rdb.Ping(ctx).Err() == nil})
	})

	// -- WebSocket Handler for Conversational Research (DYNAMIC) ---------
	r.GET("/ws/projects/:id/events", func(c *gin.Context) {
		id := c.Param("id")
		conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
		if err != nil {
			logger.Error("WebSocket upgrade failed", zap.Error(err))
			return
		}
		defer conn.Close()

		logger.Info("Research mission session active", zap.String("mission_id", id))

		// 1. Subscribe to Real-Time events from Python via Redis PubSub
		pubsub := rdb.Subscribe(ctx, "mission:"+id+":events")
		defer pubsub.Close()

		// Stream Redis events to WebSocket in the background
		go func() {
			ch := pubsub.Channel()
			for msg := range ch {
				var event AgentEvent
				if err := json.Unmarshal([]byte(msg.Payload), &event); err == nil {
					conn.WriteJSON(event)
				}
			}
		}()

		// Initial connection greeting
		conn.WriteJSON(AgentEvent{
			Type:    "system",
			Message: "SARANG Research Swarm Connected. Lead Researcher ready.",
			Agent:   "system",
		})

		// Main loop to handle incoming user questions
		for {
			var msg ChatMessage
			err := conn.ReadJSON(&msg)
			if err != nil {
				break
			}
			logger.Info("User message received", zap.String("message", msg.Message))
			go relayToPython(conn, msg)
		}
	})

	// -- REST Endpoints --------------------------------------------------
	v1 := r.Group("/v1")
	{
		v1.POST("/missions", createMission)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	logger.Info("SARANG Gateway launching", zap.String("port", port))
	r.Run(":" + port)
}

func createMission(c *gin.Context) {
	var req struct {
		Goal string `json:"goal" binding:"required"`
		Name string `json:"name" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid mission request"})
		return
	}

	missionID := uuid.New().String()
	mission := ResearchMission{
		ID:          missionID,
		Name:        req.Name,
		Goal:        req.Goal,
		Status:      "running",
		ProgressPct: 0,
		CreatedAt:   time.Now(),
	}

	go func() {
		payload := map[string]string{
			"mission_id": missionID,
			"goal":       req.Goal,
		}
		jsonPayload, _ := json.Marshal(payload)
		http.Post("http://localhost:8000/agents/research", "application/json", bytes.NewBuffer(jsonPayload))
	}()

	c.JSON(http.StatusAccepted, mission)
}

func relayToPython(conn *websocket.Conn, msg ChatMessage) {
	payload := map[string]string{
		"message":    msg.Message,
		"agent_role": msg.AgentRole,
	}
	if payload["agent_role"] == "" {
		payload["agent_role"] = "Lead_Researcher"
	}

	jsonPayload, _ := json.Marshal(payload)
	resp, err := http.Post("http://localhost:8000/agents/chat", "application/json", bytes.NewBuffer(jsonPayload))
	if err != nil {
		conn.WriteJSON(AgentEvent{Type: "error", Message: "Intelligence service unavailable", Agent: "system"})
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	var agentResp struct {
		Content   string `json:"content"`
		AgentRole string `json:"agent_role"`
	}
	json.Unmarshal(body, &agentResp)

	conn.WriteJSON(AgentEvent{
		Type:    "message",
		Message: agentResp.Content,
		Agent:   agentResp.AgentRole,
	})
}
