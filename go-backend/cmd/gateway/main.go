// Gateway Service — main entrypoint
// Starts the Fiber HTTP server with all middleware and routes.
// This is the single public-facing entry point for the entire system.
package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/compress"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/gateway/handler"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/gateway/middleware"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/auth"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	redisclient "github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/redis"
)

func main() {
	ctx := context.Background()

	// ── Config ─────────────────────────────────────────────────────────────
	cfg, err := config.Load("gateway")
	if err != nil {
		panic("config load failed: " + err.Error())
	}

	// ── Logger ─────────────────────────────────────────────────────────────
	if err := logger.Init(cfg.ServiceName, cfg.Observ.LogLevel, cfg.Observ.LogJSON); err != nil {
		panic("logger init failed: " + err.Error())
	}
	defer logger.Sync()
	log := logger.L()

	log.Info("gateway starting",
		zap.String("env", cfg.Env),
		zap.String("addr", cfg.Addr()),
	)

	// ── Dependencies ────────────────────────────────────────────────────────
	pgPool, err := db.New(ctx, &cfg.Postgres)
	if err != nil {
		log.Fatal("postgres connection failed", zap.Error(err))
	}
	defer pgPool.Close()

	redisClient, err := redisclient.New(ctx, &cfg.Redis)
	if err != nil {
		log.Fatal("redis connection failed", zap.Error(err))
	}
	defer redisClient.Close()

	authSvc, err := auth.New(&cfg.Auth)
	if err != nil {
		log.Warn("auth service init failed (JWT/OAuth disabled)", zap.Error(err))
		authSvc = nil
	}

	_ = pgPool
	_ = redisClient

	// ── Fiber App ───────────────────────────────────────────────────────────
	app := fiber.New(fiber.Config{
		AppName:               "AI Org Gateway",
		ReadTimeout:           cfg.Server.ReadTimeout,
		WriteTimeout:          cfg.Server.WriteTimeout,
		BodyLimit:             cfg.Server.MaxBodyMB * 1024 * 1024,
		DisableStartupMessage: true,
		ErrorHandler: func(c *fiber.Ctx, err error) error {
			code := fiber.StatusInternalServerError
			if e, ok := err.(*fiber.Error); ok {
				code = e.Code
			}
			return c.Status(code).JSON(fiber.Map{
				"error":    err.Error(),
				"trace_id": c.Locals("trace_id"),
			})
		},
	})

	// ── Global Middleware (order matters) ───────────────────────────────────
	app.Use(recover.New())  // Never crash on panic
	app.Use(compress.New()) // Gzip responses
	app.Use(middleware.CORS())
	app.Use(middleware.RequestLogger())
	if authSvc != nil {
		app.Use(middleware.JWTAuth(authSvc))
	}

	// ── Routes ──────────────────────────────────────────────────────────────
	// Health probes (no auth required)
	app.Get("/healthz", handler.HealthCheck)
	app.Get("/readyz", handler.ReadyCheck)

	// REST API v1
	v1 := app.Group("/v1")

	// Projects
	projects := v1.Group("/projects")
	projects.Post("/", handler.CreateProject)
	projects.Get("/", handler.ListProjects)
	projects.Get("/:id", handler.GetProject)
	projects.Delete("/:id", handler.CancelProject)
	projects.Get("/:id/cost", handler.GetCostReport)

	// WebSocket stream (upgrades to ws-hub)
	// app.Get("/v1/projects/:id/stream", websocketProxy)

	// Auth (Google OAuth — parked for Phase 4)
	// auth := v1.Group("/auth")
	// auth.Get("/google", authHandler.GoogleRedirect)
	// auth.Get("/google/callback", authHandler.GoogleCallback)

	log.Info("routes registered", zap.Int("count", len(app.GetRoutes())))

	// ── Graceful Shutdown ───────────────────────────────────────────────────
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)

	go func() {
		log.Info("http server listening", zap.String("addr", cfg.Addr()))
		if err := app.Listen(cfg.Addr()); err != nil {
			log.Error("server error", zap.Error(err))
		}
	}()

	<-quit
	log.Info("shutdown signal received — draining connections")

	shutdownCtx, cancel := context.WithTimeout(ctx, cfg.Server.ShutdownTimeout)
	defer cancel()

	if err := app.ShutdownWithContext(shutdownCtx); err != nil {
		log.Error("shutdown error", zap.Error(err))
	}

	log.Info("gateway stopped cleanly")
	_ = time.Now() // ensure time import is used
}
