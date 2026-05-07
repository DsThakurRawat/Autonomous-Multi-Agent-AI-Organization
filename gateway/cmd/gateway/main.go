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
	"github.com/gorilla/websocket"
	"go.uber.org/zap"
)

// -- Data Models -----------------------------------------------------

type AgentEvent struct {
	Type      string      `json:"type"`
	Message   string      `json:"message"`
	Agent     string      `json:"agent"`
	Level     string      `json:"level,omitempty"`
	Timestamp string      `json:"timestamp,omitempty"`
	SessionID string      `json:"session_id,omitempty"`
	Data      interface{} `json:"data,omitempty"`
}

type ChatRequest struct {
	Message   string `json:"message" binding:"required"`
	Role      string `json:"role"`
	SessionID string `json:"session_id"`
}

var (
	logger   *zap.Logger
	rdb      *redis.Client
	ctx      = context.Background()
	upgrader = websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool { return true },
	}
	pythonURL string
)

func init() {
	logger, _ = zap.NewDevelopment()
	
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "localhost:6379"
	}
	rdb = redis.NewClient(&redis.Options{
		Addr: redisURL,
	})

	pythonURL = os.Getenv("PYTHON_AGENT_URL")
	if pythonURL == "" {
		pythonURL = "http://localhost:8000"
	}
}

func main() {
	r := gin.New()
	r.Use(gin.Recovery())
	
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"*"},
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "SARANG Gateway Online"})
	})

	// --- Session Management Proxy ---
	r.GET("/sessions", proxyToPython)
	r.POST("/sessions", proxyToPython)
	r.GET("/sessions/:id/messages", proxyToPython)
	r.DELETE("/sessions/:id", proxyToPython)

	// REST proxy: forward /agents/chat to Python intelligence service
	r.POST("/agents/chat", func(c *gin.Context) {
		var req ChatRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}
		if req.Role == "" {
			req.Role = "Research_Intelligence"
		}

		payload, _ := json.Marshal(req)
		client := http.Client{Timeout: 90 * time.Second}

		resp, err := client.Post(pythonURL+"/agents/chat", "application/json", bytes.NewBuffer(payload))
		if err != nil {
			c.JSON(http.StatusBadGateway, gin.H{"error": "Intelligence Service Offline"})
			return
		}
		defer resp.Body.Close()

		body, _ := io.ReadAll(resp.Body)
		c.Data(resp.StatusCode, "application/json", body)
	})

	// WebSocket: bidirectional chat with Redis pubsub relay
	r.GET("/ws/chat", func(c *gin.Context) {
		conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
		if err != nil {
			logger.Error("WebSocket upgrade failed", zap.Error(err))
			return
		}
		defer conn.Close()
		logger.Info("New WebSocket client connected")

		pubsub := rdb.Subscribe(ctx, "sarang:events")
		defer pubsub.Close()

		// Goroutine: relay Redis events → WebSocket
		go func() {
			ch := pubsub.Channel()
			for msg := range ch {
				var event AgentEvent
				if err := json.Unmarshal([]byte(msg.Payload), &event); err == nil {
					logger.Info("Relaying event to WebSocket", zap.String("type", event.Type), zap.String("session", event.SessionID))
					conn.WriteJSON(event)
				}
			}
		}()

		conn.WriteJSON(AgentEvent{
			Type:    "system",
			Message: "SARANG Research Swarm Connected.",
			Agent:   "system",
		})

		for {
			var req ChatRequest
			if err := conn.ReadJSON(&req); err != nil {
				break
			}
			go relayToAgents(conn, req)
		}
	})

	port := os.Getenv("PORT")
	if port == "" { port = "8080" }
	logger.Info("SARANG Gateway starting", zap.String("port", port), zap.String("python_url", pythonURL))
	r.Run(":" + port)
}

func proxyToPython(c *gin.Context) {
	// Simple proxy to forward request to Python backend
	client := &http.Client{}
	url := pythonURL + c.Request.URL.Path
	if c.Request.URL.RawQuery != "" {
		url += "?" + c.Request.URL.RawQuery
	}

	req, err := http.NewRequest(c.Request.Method, url, c.Request.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	req.Header = c.Request.Header
	resp, err := client.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, gin.H{"error": "Intelligence Service Offline"})
		return
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	c.Data(resp.StatusCode, "application/json", body)
}

func relayToAgents(conn *websocket.Conn, req ChatRequest) {
	if req.Role == "" { req.Role = "Research_Intelligence" }
	
	payload, _ := json.Marshal(req)
	client := http.Client{Timeout: 90 * time.Second}
	
	resp, err := client.Post(pythonURL+"/agents/chat", "application/json", bytes.NewBuffer(payload))
	if err != nil {
		conn.WriteJSON(AgentEvent{Type: "error", Message: "Intelligence Service Offline", Agent: "system"})
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
		SessionID: req.SessionID,
	})
}
