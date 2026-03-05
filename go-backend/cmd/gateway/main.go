// Gateway Service — main entrypoint
// Starts the Fiber HTTP server with all middleware and routes.
// This is the single public-facing entry point for the entire system.
package main

import (
	"context"
	"os"
	"os/signal"
	"syscall"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/compress"
	"github.com/gofiber/fiber/v2/middleware/recover"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/gateway/grpcclient"
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

	log.Info("gateway starting", zap.String("env", cfg.Env), zap.String("addr", cfg.Addr()))

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

	orchTarget := os.Getenv("AI_ORG_ORCHESTRATOR_TARGET")
	if orchTarget == "" {
		orchTarget = "localhost:9090"
	}

	orchClient, err := grpcclient.NewOrchestratorClient(ctx, orchTarget)
	if err != nil {
		log.Fatal("failed to connect to orchestrator", zap.Error(err))
	}
	defer orchClient.Close()

	hdlr := handler.NewHandler(orchClient, pgPool)
	settingsHdlr := handler.NewSettingsHandler(pgPool)
	tasksHdlr := handler.NewTasksHandler(pgPool)
	var oauthHdlr *handler.OAuthHandler
	if authSvc != nil {
		oauthHdlr = handler.NewOAuthHandler(authSvc, pgPool)
	}

	// ── Fiber App ───────────────────────────────────────────────────────────
	app := fiber.New(fiber.Config{
		AppName: "AI Org Gateway",
		// BodyLimit, timeouts etc mapping from cfg.Server would be here
		DisableStartupMessage: true,
	})

	app.Use(recover.New())
	app.Use(compress.New())
	app.Use(middleware.CORS())
	app.Use(middleware.RequestLogger())

	// ── Auth middleware — two modes ───────────────────────────────────────────
	if middleware.LocalMode() {
		// LOCAL MODE: AUTH_DISABLED=true
		// No login required. Every request gets a fixed local-user identity injected.
		// Perfect for self-hosted / personal use — just set API keys in .env.
		log.Info("⚠️  AUTH_DISABLED=true — running in local mode (no login required)")
		app.Use(middleware.LocalAuth())
	} else {
		// SAAS MODE: Google OAuth + RS256 JWT cookie
		// Register OAuth endpoints BEFORE JWTAuth so they are accessible without a token.
		if authSvc != nil && oauthHdlr != nil {
			app.Get("/auth/google", oauthHdlr.GoogleLogin)
			app.Get("/auth/google/callback", oauthHdlr.GoogleCallback)
		}
		if authSvc != nil {
			app.Use(middleware.JWTAuth(authSvc))
		}
	}

	v1 := app.Group("/v1")
	projects := v1.Group("/projects")
	projects.Post("/", hdlr.CreateProject)
	projects.Get("/", hdlr.ListProjects)
	projects.Get("/:id", hdlr.GetProject)
	projects.Delete("/:id", hdlr.CancelProject)
	projects.Get("/:id/cost", hdlr.GetCostReport)
	projects.Get("/:id/tasks", tasksHdlr.GetProjectTasks)
	projects.Get("/:id/events", tasksHdlr.GetProjectEvents)

	// Settings — LLM key management + agent model prefs
	settings := v1.Group("/settings")
	settings.Post("/keys", settingsHdlr.AddKey)
	settings.Get("/keys", settingsHdlr.ListKeys)
	settings.Delete("/keys/:id", settingsHdlr.DeleteKey)
	settings.Post("/agent-prefs", settingsHdlr.SetAgentPref)
	settings.Get("/agent-prefs", settingsHdlr.GetAgentPrefs)
	settings.Delete("/agent-prefs/:role", settingsHdlr.DeleteAgentPref)

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, os.Interrupt, syscall.SIGTERM)

	go func() {
		log.Info("http server listening", zap.String("addr", cfg.Addr()))
		if err := app.Listen(cfg.Addr()); err != nil {
			log.Error("server error", zap.Error(err))
		}
	}()

	<-quit
	log.Info("gateway shutting down")
	_ = app.Shutdown()
	log.Info("gateway stopped cleanly")
}
