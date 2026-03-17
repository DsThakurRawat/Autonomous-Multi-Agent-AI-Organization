// Orchestrator Service — main entrypoint
// Manages the DAG execution engine: plans tasks, dispatches to Kafka,
// processes results, handles retries, and tracks project lifecycle.
package main

import (
	"context"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gofiber/fiber/v2"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/health"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/orchestrator/server"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/kafka"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	pb "github.com/DsThakurRawat/autonomous-org/go-backend/proto/gen/orchestrator"
)

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	cfg, err := config.Load("orchestrator")
	if err != nil {
		log.Fatalf("config load failed: %v", err)
	}

	if err := logger.Init(cfg.ServiceName, cfg.Observ.LogLevel, cfg.Observ.LogJSON); err != nil {
		log.Fatalf("logger init failed: %v", err)
	}
	defer logger.Sync()
	log := logger.L()

	log.Info("orchestrator starting", zap.String("env", cfg.Env))

	// ── Postgres ─────────────────────────────────────────────────────────
	pgPool, err := db.New(ctx, &cfg.Postgres)
	if err != nil {
		log.Fatal("postgres failed", zap.Error(err))
	}
	defer pgPool.Close()

	// ── Redis ─────────────────────────────────────────────────────────────
	redisClient, err := db.NewRedis(ctx, &cfg.Redis)
	if err != nil {
		log.Fatal("redis failed", zap.Error(err))
	}
	defer redisClient.Close()

	// ── Kafka Producer (for publishing tasks) ────────────────────────────
	producer, err := kafka.NewProducer(&cfg.Kafka)
	if err != nil {
		log.Fatal("kafka producer failed", zap.Error(err))
	}
	defer producer.Close()
	
	healthOrch := health.NewHealthOrchestrator(pgPool, redisClient)
	// Optionally wait for readiness before moving further in production
	// healthOrch.WaitUntilReady(ctx, 10*time.Second) 

	resultHandler := server.NewResultHandler(pgPool, redisClient, producer)

	// ── Kafka Consumer (for consuming results) ────────────────────────────
	resultConsumer, err := kafka.NewConsumerGroup(
		&cfg.Kafka,
		"orchestrator-results",
		[]string{cfg.Kafka.TopicResults},
		func(ctx context.Context, msg kafka.Message) error {
			return resultHandler.Handle(ctx, msg)
		},
	)
	if err != nil {
		log.Fatal("kafka consumer failed", zap.Error(err))
	}

	// ── Kafka Consumer (for heartbeats) ──────────────────────────────────
	hbHandler := server.NewHeartbeatHandler(redisClient)
	hbConsumer, err := kafka.NewConsumerGroup(
		&cfg.Kafka,
		"orchestrator-heartbeats",
		[]string{cfg.Kafka.TopicHB}, // ai-org-heartbeats
		func(ctx context.Context, msg kafka.Message) error {
			return hbHandler.Handle(ctx, msg)
		},
	)
	if err != nil {
		log.Fatal("heartbeat consumer failed", zap.Error(err))
	}

	// ── Start Consumers in background ─────────────────────────────────────
	go func() {
		if err := resultConsumer.Consume(ctx); err != nil {
			log.Error("result consumer stopped", zap.Error(err))
		}
	}()
	go func() {
		if err := hbConsumer.Consume(ctx); err != nil {
			log.Error("heartbeat consumer stopped", zap.Error(err))
		}
	}()

	// ── gRPC Server (for Gateway calls) ─────────────────────────────────
	lis, err := net.Listen("tcp", cfg.GRPCAddr())
	if err != nil {
		log.Fatal("failed to listen", zap.Error(err))
	}

	grpcServer := grpc.NewServer()

	orchServer := server.NewOrchestratorServer(pgPool, redisClient, producer)
	pb.RegisterOrchestratorServiceServer(grpcServer, orchServer)

	// Register reflection service on gRPC server (useful for evans / grpcui)
	reflection.Register(grpcServer)

	// ── Lease Monitor (background cleanup) ──────────────────────────────
	monitor := server.NewLeaseMonitor(pgPool, redisClient)
	go monitor.Start(ctx, 30*time.Second)

	go func() {
		log.Info("orchestrator grpc listening", zap.String("grpc_addr", cfg.GRPCAddr()))
		if err := grpcServer.Serve(lis); err != nil {
			log.Error("grpc serve error", zap.Error(err))
		}
	}()

	// ── Health Check (HTTP) ──────────────────────────────────────────────
	healthApp := fiber.New(fiber.Config{DisableStartupMessage: true})
	healthApp.Get("/healthz", func(c *fiber.Ctx) error {
		stats, healthy := healthOrch.CheckAll(c.Context())
		if !healthy {
			return c.Status(503).JSON(fiber.Map{
				"status":       "unhealthy",
				"dependencies": stats,
			})
		}
		return c.JSON(fiber.Map{
			"status":       "ok",
			"service":      "orchestrator",
			"dependencies": stats,
		})
	})
	go func() {
		if err := healthApp.Listen(":9091"); err != nil {
			log.Error("health check server error", zap.Error(err))
		}
	}()

	log.Info("orchestrator ready",
		zap.Strings("kafka_brokers", cfg.Kafka.Brokers),
	)

	// ── Graceful Shutdown ─────────────────────────────────────────────────
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)
	<-quit

	log.Info("orchestrator shutting down")
	grpcServer.GracefulStop()
	cancel()
	_ = resultConsumer.Close()
	log.Info("orchestrator stopped cleanly")
}
