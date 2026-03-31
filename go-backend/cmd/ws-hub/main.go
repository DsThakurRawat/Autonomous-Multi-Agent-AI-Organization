// WebSocket Hub Service — main entrypoint
// Consumes Kafka ai-org-events.* topics and fans out to connected dashboard clients.
// Uses Redis pub/sub for cross-pod event distribution (sticky routing via Nginx).
package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/gofiber/contrib/websocket"
	"github.com/gofiber/fiber/v2"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/kafka"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// registry maps project_id → set of active WebSocket connections.
type registry struct {
	mu    sync.RWMutex
	conns map[string]map[*websocket.Conn]struct{}
}

func newRegistry() *registry {
	return &registry{conns: make(map[string]map[*websocket.Conn]struct{})}
}

func (r *registry) add(projectID string, conn *websocket.Conn) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.conns[projectID] == nil {
		r.conns[projectID] = make(map[*websocket.Conn]struct{})
	}
	r.conns[projectID][conn] = struct{}{}
}

func (r *registry) remove(projectID string, conn *websocket.Conn) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.conns[projectID], conn)
}

// broadcast sends msg JSON to every connection registered for projectID.
func (r *registry) broadcast(projectID string, msg any) {
	r.mu.RLock()
	conns := r.conns[projectID]
	r.mu.RUnlock()

	data, _ := json.Marshal(msg)
	for conn := range conns {
		if err := conn.WriteMessage(1 /* TextMessage */, data); err != nil {
			logger.L().Debug("ws write failed", zap.Error(err))
		}
	}
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg, err := config.Load("ws-hub")
	if err != nil {
		log.Fatalf("config load failed: %v", err)
	}
	if err := logger.Init(cfg.ServiceName, cfg.Observ.LogLevel, cfg.Observ.LogJSON); err != nil {
		log.Fatalf("logger init failed: %v", err)
	}
	defer logger.Sync()
	log := logger.L()

	rdb := redis.NewClient(&redis.Options{
		Addr: getEnv("REDIS_ADDR", "localhost:6379"),
	})

	reg := newRegistry()

	// ── Kafka Consumer (all project event topics) ─────────────────────────
	eventConsumer, err := kafka.NewConsumerGroup(
		&cfg.Kafka,
		"ws-hub-events",
		[]string{cfg.Kafka.TopicEvents},
		func(ctx context.Context, msg kafka.Message) error {
			// Key format: "{project_id}"
			projectID := msg.Key
			if projectID == "" {
				return nil
			}

			var event map[string]any
			if err := json.Unmarshal(msg.Value, &event); err != nil {
				return fmt.Errorf("ws-hub: unmarshal event: %w", err)
			}

			reg.broadcast(projectID, event)

			// Store in Redis Stream for replay (last 100 events)
			err := rdb.XAdd(ctx, &redis.XAddArgs{
				Stream: "events:" + projectID,
				MaxLen: 100,
				Values: map[string]interface{}{"payload": string(msg.Value)},
			}).Err()
			if err != nil {
				log.Warn("failed to store event in redis stream", zap.Error(err))
			}

			log.Debug("event broadcast",
				zap.String("project_id", projectID),
				zap.String("event_type", fmt.Sprintf("%v", event["event_type"])),
			)
			return nil
		},
	)
	if err != nil {
		log.Fatal("kafka consumer failed", zap.Error(err))
	}

	go func() {
		if err := eventConsumer.Consume(ctx); err != nil {
			log.Error("event consumer stopped", zap.Error(err))
		}
	}()

	// ── Fiber WebSocket Server ─────────────────────────────────────────────
	app := fiber.New(fiber.Config{DisableStartupMessage: true})

	app.Use("/ws", func(c *fiber.Ctx) error {
		if websocket.IsWebSocketUpgrade(c) {
			return c.Next()
		}
		return fiber.ErrUpgradeRequired
	})

	app.Get("/ws/projects/:id/events", websocket.New(func(conn *websocket.Conn) {
		projectID := conn.Params("id")
		
		// Replay historical events on connect
		events, err := rdb.XRange(context.Background(), "events:"+projectID, "-", "+").Result()
		if err == nil {
			for _, e := range events {
				if payload, ok := e.Values["payload"].(string); ok {
					_ = conn.WriteMessage(1, []byte(payload))
				}
			}
		}

		reg.add(projectID, conn)
		defer reg.remove(projectID, conn)

		log.Info("ws client connected & replayed", zap.String("project_id", projectID))

		// Keep alive — wait for client disconnect or error
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				log.Debug("ws client disconnected", zap.String("project_id", projectID))
				break
			}
		}
	}))

	// Support for landing page which might use /stream
	app.Get("/ws/projects/:id/stream", websocket.New(func(conn *websocket.Conn) {
		projectID := conn.Params("id")
		reg.add(projectID, conn)
		defer reg.remove(projectID, conn)
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				break
			}
		}
	}))

	app.Get("/ws/events", websocket.New(func(conn *websocket.Conn) {
		log.Info("global ws client connected")
		for {
			if _, _, err := conn.ReadMessage(); err != nil {
				break
			}
		}
	}))

	app.Get("/healthz", func(c *fiber.Ctx) error {
		return c.JSON(fiber.Map{"status": "ok", "service": "ws-hub"})
	})

	log.Info("ws-hub ready", zap.String("addr", cfg.Addr()))

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)

	go func() {
		if err := app.Listen(cfg.Addr()); err != nil {
			log.Error("ws-hub server error", zap.Error(err))
		}
	}()

	<-quit
	log.Info("ws-hub shutting down")
	cancel()
	_ = app.Shutdown()
	log.Info("ws-hub stopped cleanly")
}
