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
	Type    string      `json:"type"`
	Message string      `json:"message"`
	Agent   string      `json:"agent"`
	Data    interface{} `json:"data,omitempty"`
}

type ChatRequest struct {
	Message string `json:"message" binding:"required"`
	Role    string `json:"role"`
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
	logger, _ = zap.NewDevelopment()
	
	redisURL := os.Getenv("REDIS_URL")
	if redisURL == "" {
		redisURL = "localhost:6379"
	}
	rdb = redis.NewClient(&redis.Options{
		Addr: redisURL,
	})
}

func main() {
	r := gin.New()
	r.Use(gin.Recovery())
	
	r.Use(cors.New(cors.Config{
		AllowAllOrigins: true,
		AllowMethods:    []string{"GET", "POST", "OPTIONS"},
		AllowHeaders:    []string{"Origin", "Content-Type", "Accept"},
		MaxAge:          12 * time.Hour,
	}))

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "SARANG Gateway Online"})
	})

	r.GET("/ws/chat", func(c *gin.Context) {
		conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		pubsub := rdb.Subscribe(ctx, "sarang:events")
		defer pubsub.Close()

		go func() {
			ch := pubsub.Channel()
			for msg := range ch {
				var event AgentEvent
				if err := json.Unmarshal([]byte(msg.Payload), &event); err == nil {
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
	r.Run(":" + port)
}

func relayToAgents(conn *websocket.Conn, req ChatRequest) {
	if req.Role == "" { req.Role = "Research_Intelligence" }
	
	payload, _ := json.Marshal(req)
	client := http.Client{Timeout: 90 * time.Second}
	
	resp, err := client.Post("http://localhost:8000/agents/chat", "application/json", bytes.NewBuffer(payload))
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
	})
}
