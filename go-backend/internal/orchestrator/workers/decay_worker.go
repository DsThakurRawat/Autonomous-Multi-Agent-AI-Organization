package workers

import (
	"context"
	"time"

	"go.uber.org/zap"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// DecayWorker manages memory relevance decay.
type DecayWorker struct {
	db       *db.Pool
	interval time.Duration
}

// NewDecayWorker creates a new DecayWorker instance.
func NewDecayWorker(pool *db.Pool, interval time.Duration) *DecayWorker {
	if interval == 0 {
		interval = 1 * time.Hour
	}
	return &DecayWorker{
		db:       pool,
		interval: interval,
	}
}

// Start runs the periodic decay routine.
func (w *DecayWorker) Start(ctx context.Context) {
	ticker := time.NewTicker(w.interval)
	defer ticker.Stop()

	logger.L().Info("memory decay worker started", zap.Duration("interval", w.interval))

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			w.runDecay(ctx)
		}
	}
}

func (w *DecayWorker) runDecay(ctx context.Context) {
	log := logger.L()

	// 1. Reduce relevance score of all facts (linear decay)
	// We assume a 'facts' table exists or will be added for L2/L3 memory.
	// For now, we apply it to tasks' 'relevance_score' if we decide to add that column, 
	// or we target the future-proof L2 memory table.
	
	decayQuery := `UPDATE memory_facts SET relevance_score = relevance_score * 0.9 WHERE relevance_score > 0`
	tag, err := w.db.Exec(ctx, decayQuery)
	if err != nil {
		log.Error("failed to decay memory relevance", zap.Error(err))
	} else {
		log.Info("memory decay applied", zap.Int64("rows_affected", tag.RowsAffected()))
	}

	// 2. Prune irrelevance (below 0.1)
	pruneQuery := `DELETE FROM memory_facts WHERE relevance_score < 0.1 AND pinned = false`
	tag, err = w.db.Exec(ctx, pruneQuery)
	if err != nil {
		log.Error("failed to prune stale memory", zap.Error(err))
	} else if tag.RowsAffected() > 0 {
		log.Info("stale memory pruned", zap.Int64("rows_affected", tag.RowsAffected()))
	}
}
