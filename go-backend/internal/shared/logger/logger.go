// Package logger provides a structured, leveled logger using uber-go/zap.
// In production (log_json=true) it emits JSON for CloudWatch/Loki.
// In local mode it emits human-readable colored output.
package logger

import (
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
)

var global *zap.Logger

// Init initialises the global logger. Call once at service startup.
// level: "debug" | "info" | "warn" | "error"
// jsonOutput: true in production
func Init(serviceName, level string, jsonOutput bool) error {
	lvl, err := zapcore.ParseLevel(level)
	if err != nil {
		lvl = zapcore.InfoLevel
	}

	var cfg zap.Config
	if jsonOutput {
		cfg = zap.NewProductionConfig()
	} else {
		cfg = zap.NewDevelopmentConfig()
		cfg.EncoderConfig.EncodeLevel = zapcore.CapitalColorLevelEncoder
	}

	cfg.Level = zap.NewAtomicLevelAt(lvl)

	log, err := cfg.Build(
		zap.Fields(
			zap.String("service", serviceName),
		),
		zap.AddCaller(),
		zap.AddStacktrace(zapcore.ErrorLevel),
	)
	if err != nil {
		return err
	}

	global = log
	zap.ReplaceGlobals(log)
	return nil
}

// L returns the global logger. Panics if Init was not called.
func L() *zap.Logger {
	if global == nil {
		// Safe fallback — never crash on missing init
		global, _ = zap.NewDevelopment()
	}
	return global
}

// S returns the global sugared logger (printf-style).
func S() *zap.SugaredLogger {
	return L().Sugar()
}

// With returns a child logger with the given fields always attached.
func With(fields ...zap.Field) *zap.Logger {
	return L().With(fields...)
}

// Sync flushes buffered log entries. Call at service shutdown.
func Sync() {
	_ = L().Sync()
}
