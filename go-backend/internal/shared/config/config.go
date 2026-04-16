// Package config provides centralized configuration loading for all Go services.
// Config is loaded from environment variables → YAML file → defaults, in that priority order.
package config

import (
	"fmt"
	"strings"
	"time"

	"github.com/spf13/viper"
)

// Config is the root configuration struct shared across all services.
// Each service embeds only the sections relevant to it.
type Config struct {
	// Service identity
	ServiceName string `mapstructure:"service_name"`
	Env         string `mapstructure:"env"` // local | staging | production

	Server   ServerConfig   `mapstructure:"server"`
	Postgres PostgresConfig `mapstructure:"postgres"`
	Redis    RedisConfig    `mapstructure:"redis"`
	Kafka    KafkaConfig    `mapstructure:"kafka"`
	Auth     AuthConfig     `mapstructure:"auth"`
	Observ   ObservConfig   `mapstructure:"observability"`
	Budget   BudgetConfig   `mapstructure:"budget"`
	Gateway  GatewayConfig  `mapstructure:"gateway"`
}

type ServerConfig struct {
	Host            string        `mapstructure:"host"`
	Port            int           `mapstructure:"port"`
	GRPCPort        int           `mapstructure:"grpc_port"`
	ReadTimeout     time.Duration `mapstructure:"read_timeout"`
	WriteTimeout    time.Duration `mapstructure:"write_timeout"`
	ShutdownTimeout time.Duration `mapstructure:"shutdown_timeout"`
	MaxBodyMB       int           `mapstructure:"max_body_mb"`
}

type PostgresConfig struct {
	DSN             string        `mapstructure:"dsn"`
	MaxConns        int32         `mapstructure:"max_conns"`
	MinConns        int32         `mapstructure:"min_conns"`
	MaxConnLifetime time.Duration `mapstructure:"max_conn_lifetime"`
	MaxConnIdleTime time.Duration `mapstructure:"max_conn_idle_time"`
}

type RedisConfig struct {
	Addr     string `mapstructure:"addr"` // "localhost:6379" or cluster addrs comma-separated
	Password string `mapstructure:"password"`
	DB       int    `mapstructure:"db"`
	Cluster  bool   `mapstructure:"cluster"` // true → use cluster client
}

type KafkaConfig struct {
	Brokers       []string `mapstructure:"brokers"`
	ConsumerGroup string   `mapstructure:"consumer_group"`
	// Topic names
	TopicTasks   string `mapstructure:"topic_tasks"`      // ai-org-tasks
	TopicResults string `mapstructure:"topic_results"`    // ai-org-results
	TopicEvents  string `mapstructure:"topic_events"`     // ai-org-events
	TopicHB      string `mapstructure:"topic_heartbeats"` // ai-org-heartbeats
}

type AuthConfig struct {
	JWTPrivateKeyPath  string        `mapstructure:"jwt_private_key_path"`
	JWTPublicKeyPath   string        `mapstructure:"jwt_public_key_path"`
	JWTAccessExpiry    time.Duration `mapstructure:"jwt_access_expiry"`
	JWTRefreshExpiry   time.Duration `mapstructure:"jwt_refresh_expiry"`
	GoogleClientID     string        `mapstructure:"google_client_id"`
	GoogleClientSecret string        `mapstructure:"google_client_secret"`
	GoogleRedirectURL  string        `mapstructure:"google_redirect_url"`
}

type ObservConfig struct {
	OTLPEndpoint    string  `mapstructure:"otlp_endpoint"`     // Jaeger / Honeycomb
	TraceSampleRate float64 `mapstructure:"trace_sample_rate"` // 0.0–1.0
	LogLevel        string  `mapstructure:"log_level"`         // debug | info | warn | error
	LogJSON         bool    `mapstructure:"log_json"`          // true in production
}

type BudgetConfig struct {
	DefaultMaxCostUSD  float64 `mapstructure:"default_max_cost_usd"`
	DefaultMaxTokens   int64   `mapstructure:"default_max_tokens"`
	EnforcementEnabled bool    `mapstructure:"enforcement_enabled"`
}

type GatewayConfig struct {
	RateLimitLimit int64         `mapstructure:"rate_limit_limit"`
	RateLimitWindow time.Duration `mapstructure:"rate_limit_window"`
	IdempotencyTTL  time.Duration `mapstructure:"idempotency_ttl"`
	SecurityBinPath string        `mapstructure:"security_bin_path"`
	OTelEndpoint    string        `mapstructure:"otel_endpoint"`
	CORSOrigins     string        `mapstructure:"cors_origins"`
}

// Load reads config from env vars and optional config.yaml.
// Environment variables use the prefix "AI_ORG_" and "__" as delimiter
// (e.g. AI_ORG_SERVER__PORT=8080 → Config.Server.Port=8080)
func Load(serviceName string) (*Config, error) {
	v := viper.New()

	// Defaults
	v.SetDefault("service_name", serviceName)
	v.SetDefault("env", "local")
	v.SetDefault("server.host", "0.0.0.0")
	v.SetDefault("server.port", 8080)
	v.SetDefault("server.grpc_port", 9090)
	v.SetDefault("server.read_timeout", "30s")
	v.SetDefault("server.write_timeout", "60s")
	v.SetDefault("server.shutdown_timeout", "15s")
	v.SetDefault("server.max_body_mb", 16)

	v.SetDefault("postgres.dsn", "")
	v.SetDefault("postgres.max_conns", 25)
	v.SetDefault("postgres.min_conns", 5)
	v.SetDefault("postgres.max_conn_lifetime", "1h")
	v.SetDefault("postgres.max_conn_idle_time", "30m")

	v.SetDefault("redis.addr", "localhost:6379")
	v.SetDefault("redis.password", "")
	v.SetDefault("redis.db", 0)
	v.SetDefault("redis.cluster", false)

	v.SetDefault("kafka.brokers", []string{"localhost:9092"})
	v.SetDefault("kafka.topic_tasks", "ai-org-tasks")
	v.SetDefault("kafka.topic_results", "ai-org-results")
	v.SetDefault("kafka.topic_events", "ai-org-events")
	v.SetDefault("kafka.topic_heartbeats", "ai-org-heartbeats")

	v.SetDefault("auth.jwt_access_expiry", "15m")
	v.SetDefault("auth.jwt_refresh_expiry", "168h")
	v.SetDefault("observability.trace_sample_rate", 0.1)
	v.SetDefault("observability.log_level", "info")
	v.SetDefault("observability.log_json", false)
	v.SetDefault("budget.default_max_cost_usd", 10.0)
	v.SetDefault("budget.default_max_tokens", 1000000)
	v.SetDefault("budget.enforcement_enabled", true)
	v.SetDefault("gateway.rate_limit_limit", 100)
	v.SetDefault("gateway.rate_limit_window", "1m")
	v.SetDefault("gateway.idempotency_ttl", "24h")
	v.SetDefault("gateway.security_bin_path", "/usr/local/bin/security-check")
	v.SetDefault("gateway.otel_endpoint", "otel-collector:4317")
	v.SetDefault("gateway.cors_origins", "") // Default to empty (restricted), override in prod using CORS_ORIGINS

	// Load from optional YAML file
	v.SetConfigName("config")
	v.SetConfigType("yaml")
	v.AddConfigPath(".")
	v.AddConfigPath("/etc/ai-org/")
	_ = v.ReadInConfig() // Ignore if not found — env vars take precedence

	// Load from environment variables
	v.SetEnvPrefix("AI_ORG")
	v.SetEnvKeyReplacer(strings.NewReplacer(".", "__"))
	v.AutomaticEnv()
	
	// Bind explicit non-prefixed env vars (e.g. from docker-compose)
	_ = v.BindEnv("gateway.cors_origins", "CORS_ORIGINS")

	var cfg Config
	if err := v.Unmarshal(&cfg); err != nil {
		return nil, fmt.Errorf("config: unmarshal failed: %w", err)
	}

	cfg.ServiceName = serviceName
	return &cfg, nil
}

// Addr returns host:port for the HTTP server.
func (c *Config) Addr() string {
	return fmt.Sprintf("%s:%d", c.Server.Host, c.Server.Port)
}

// GRPCAddr returns host:port for the gRPC server.
func (c *Config) GRPCAddr() string {
	return fmt.Sprintf("%s:%d", c.Server.Host, c.Server.GRPCPort)
}

// IsProduction returns true when env=production.
func (c *Config) IsProduction() bool {
	return c.Env == "production"
}
