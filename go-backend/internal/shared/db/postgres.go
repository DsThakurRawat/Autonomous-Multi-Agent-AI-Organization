// Package db provides a managed pgx connection pool for Postgres.
// Uses pgx/v5 native protocol driver — no database/sql overhead.
package db

import (
	"context"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// Pool wraps pgxpool.Pool with helpers.
type Pool struct {
	*pgxpool.Pool
}

// New creates and validates a pgxpool connection pool.
// It runs a ping to confirm connectivity before returning.
func New(ctx context.Context, cfg *config.PostgresConfig) (*Pool, error) {
	poolCfg, err := pgxpool.ParseConfig(cfg.DSN)
	if err != nil {
		return nil, fmt.Errorf("db: parse DSN: %w", err)
	}

	poolCfg.MaxConns = cfg.MaxConns
	poolCfg.MinConns = cfg.MinConns
	poolCfg.MaxConnLifetime = cfg.MaxConnLifetime
	poolCfg.MaxConnIdleTime = cfg.MaxConnIdleTime

	// Log every acquired connection in debug mode
	poolCfg.ConnConfig.Tracer = &queryTracer{}

	pool, err := pgxpool.NewWithConfig(ctx, poolCfg)
	if err != nil {
		return nil, fmt.Errorf("db: create pool: %w", err)
	}

	// Validate connectivity
	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := pool.Ping(pingCtx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("db: ping failed: %w", err)
	}

	stat := pool.Stat()
	logger.L().Info("postgres connected",
		zap.Int32("max_conns", stat.MaxConns()),
		zap.Int32("idle_conns", stat.IdleConns()),
	)

	return &Pool{pool}, nil
}

// WithTx runs fn inside a serializable transaction.
// Automatically commits on success, rolls back on any error or panic.
func (p *Pool) WithTx(ctx context.Context, fn func(pgx.Tx) error) error {
	tx, err := p.Begin(ctx)
	if err != nil {
		return fmt.Errorf("db: begin tx: %w", err)
	}

	defer func() {
		if r := recover(); r != nil {
			_ = tx.Rollback(ctx)
			panic(r) // re-panic after rollback
		}
	}()

	if err := fn(tx); err != nil {
		_ = tx.Rollback(ctx)
		return err
	}

	return tx.Commit(ctx)
}

// ── Query Tracer (debug logging) ──────────────────────────────────────────────

type queryTracer struct{}

func (t *queryTracer) TraceQueryStart(ctx context.Context, _ *pgx.Conn, data pgx.TraceQueryStartData) context.Context {
	logger.L().Debug("sql query start", zap.String("sql", data.SQL))
	return ctx
}

func (t *queryTracer) TraceQueryEnd(_ context.Context, _ *pgx.Conn, data pgx.TraceQueryEndData) {
	if data.Err != nil {
		logger.L().Error("sql query error", zap.Error(data.Err))
		return
	}
	logger.L().Debug("sql query done", zap.String("tag", data.CommandTag.String()))
}
