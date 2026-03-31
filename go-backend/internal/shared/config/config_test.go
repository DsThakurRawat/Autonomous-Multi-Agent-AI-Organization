package config

import (
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoad_Defaults(t *testing.T) {
	cfg, err := Load("test-service")
	require.NoError(t, err)

	assert.Equal(t, "test-service", cfg.ServiceName)
	assert.Equal(t, "local", cfg.Env)
	assert.Equal(t, "0.0.0.0", cfg.Server.Host)
	assert.Equal(t, 8080, cfg.Server.Port)
	assert.Equal(t, 9090, cfg.Server.GRPCPort)
	assert.Equal(t, 16, cfg.Server.MaxBodyMB)
}

func TestLoad_PostgresDefaults(t *testing.T) {
	cfg, err := Load("test-service")
	require.NoError(t, err)

	assert.Equal(t, int32(25), cfg.Postgres.MaxConns)
	assert.Equal(t, int32(5), cfg.Postgres.MinConns)
}

func TestLoad_RedisDefaults(t *testing.T) {
	cfg, err := Load("test-service")
	require.NoError(t, err)

	assert.Equal(t, "localhost:6379", cfg.Redis.Addr)
	assert.Equal(t, 0, cfg.Redis.DB)
	assert.False(t, cfg.Redis.Cluster)
}

func TestLoad_KafkaDefaults(t *testing.T) {
	cfg, err := Load("test-service")
	require.NoError(t, err)

	assert.Equal(t, []string{"localhost:9092"}, cfg.Kafka.Brokers)
	assert.Equal(t, "ai-org-tasks", cfg.Kafka.TopicTasks)
	assert.Equal(t, "ai-org-results", cfg.Kafka.TopicResults)
	assert.Equal(t, "ai-org-events", cfg.Kafka.TopicEvents)
	assert.Equal(t, "ai-org-heartbeats", cfg.Kafka.TopicHB)
}

func TestLoad_BudgetDefaults(t *testing.T) {
	cfg, err := Load("test-service")
	require.NoError(t, err)

	assert.Equal(t, 10.0, cfg.Budget.DefaultMaxCostUSD)
	assert.Equal(t, int64(1000000), cfg.Budget.DefaultMaxTokens)
	assert.True(t, cfg.Budget.EnforcementEnabled)
}

func TestLoad_EnvOverrides(t *testing.T) {
	os.Setenv("AI_ORG_SERVER__PORT", "9999")
	os.Setenv("AI_ORG_ENV", "production")
	defer os.Unsetenv("AI_ORG_SERVER__PORT")
	defer os.Unsetenv("AI_ORG_ENV")

	cfg, err := Load("test-service")
	require.NoError(t, err)

	assert.Equal(t, 9999, cfg.Server.Port)
	assert.Equal(t, "production", cfg.Env)
}

func TestAddr(t *testing.T) {
	cfg, _ := Load("test-service")
	assert.Equal(t, "0.0.0.0:8080", cfg.Addr())
}

func TestGRPCAddr(t *testing.T) {
	cfg, _ := Load("test-service")
	assert.Equal(t, "0.0.0.0:9090", cfg.GRPCAddr())
}

func TestIsProduction(t *testing.T) {
	cfg, _ := Load("test-service")
	assert.False(t, cfg.IsProduction())

	cfg.Env = "production"
	assert.True(t, cfg.IsProduction())

	cfg.Env = "staging"
	assert.False(t, cfg.IsProduction())
}

func TestLoad_GatewayDefaults(t *testing.T) {
	cfg, err := Load("test-service")
	require.NoError(t, err)

	assert.Equal(t, int64(100), cfg.Gateway.RateLimitLimit)
	assert.Equal(t, "/usr/local/bin/security-check", cfg.Gateway.SecurityBinPath)
}

func TestLoad_AuthDefaults(t *testing.T) {
	cfg, err := Load("test-service")
	require.NoError(t, err)

	// JWT access expiry should be 15 minutes
	assert.NotZero(t, cfg.Auth.JWTAccessExpiry)
}
