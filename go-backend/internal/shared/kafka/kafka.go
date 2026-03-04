// Package kafka provides shared Kafka producer and consumer wrappers
// using the IBM/sarama library. Designed for exactly-once-friendly
// message delivery with structured JSON payloads.
package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/IBM/sarama"
	"go.uber.org/zap"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/config"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// ── Producer ─────────────────────────────────────────────────────────────────

// Producer is a synchronous Kafka producer.
type Producer struct {
	sp sarama.SyncProducer
}

// NewProducer creates a high-reliability synchronous producer.
// Uses Acks=All and retry logic for maximum durability.
func NewProducer(cfg *config.KafkaConfig) (*Producer, error) {
	sc := sarama.NewConfig()
	sc.Version = sarama.V3_5_0_0
	sc.Producer.Return.Successes = true
	sc.Producer.Return.Errors = true
	sc.Producer.RequiredAcks = sarama.WaitForAll     // Acks from all ISR replicas
	sc.Producer.Retry.Max = 5
	sc.Producer.Retry.Backoff = 100 * time.Millisecond
	sc.Producer.Compression = sarama.CompressionSnappy
	sc.Producer.Idempotent = true                   // Exactly-once semantics
	sc.Net.MaxOpenRequests = 1                       // Required for idempotent producer

	sp, err := sarama.NewSyncProducer(cfg.Brokers, sc)
	if err != nil {
		return nil, fmt.Errorf("kafka: create producer: %w", err)
	}

	logger.L().Info("kafka producer connected", zap.Strings("brokers", cfg.Brokers))
	return &Producer{sp: sp}, nil
}

// PublishJSON serialises v to JSON and publishes to topic with optional key.
// Returns partition and offset on success.
func (p *Producer) PublishJSON(topic, key string, v any) (int32, int64, error) {
	data, err := json.Marshal(v)
	if err != nil {
		return 0, 0, fmt.Errorf("kafka: marshal: %w", err)
	}

	msg := &sarama.ProducerMessage{
		Topic:     topic,
		Value:     sarama.ByteEncoder(data),
		Timestamp: time.Now(),
	}
	if key != "" {
		msg.Key = sarama.StringEncoder(key)
	}

	partition, offset, err := p.sp.SendMessage(msg)
	if err != nil {
		return 0, 0, fmt.Errorf("kafka: send to %s: %w", topic, err)
	}

	logger.L().Debug("kafka message published",
		zap.String("topic", topic),
		zap.String("key", key),
		zap.Int32("partition", partition),
		zap.Int64("offset", offset),
	)
	return partition, offset, nil
}

// Close shuts down the producer, flushing any buffered messages.
func (p *Producer) Close() error {
	return p.sp.Close()
}

// ── Consumer ─────────────────────────────────────────────────────────────────

// Message is a decoded Kafka message with metadata.
type Message struct {
	Topic     string
	Partition int32
	Offset    int64
	Key       string
	Value     []byte
	Timestamp time.Time
}

// HandlerFunc is the callback invoked for each consumed message.
// Return non-nil error to signal a processing failure (message will be retried
// based on your consumer group commit strategy).
type HandlerFunc func(ctx context.Context, msg Message) error

// ConsumerGroup wraps a sarama consumer group for multi-topic consumption.
type ConsumerGroup struct {
	group   sarama.ConsumerGroup
	topics  []string
	handler sarama.ConsumerGroupHandler
	cfg     *config.KafkaConfig
}

// NewConsumerGroup creates a consumer group client subscribed to topics.
func NewConsumerGroup(cfg *config.KafkaConfig, groupID string, topics []string, handler HandlerFunc) (*ConsumerGroup, error) {
	sc := sarama.NewConfig()
	sc.Version = sarama.V3_5_0_0
	sc.Consumer.Group.Rebalance.GroupStrategies = []sarama.BalanceStrategy{sarama.NewBalanceStrategyRoundRobin()}
	sc.Consumer.Offsets.Initial = sarama.OffsetNewest
	sc.Consumer.Offsets.AutoCommit.Enable = true
	sc.Consumer.Offsets.AutoCommit.Interval = 1 * time.Second

	group, err := sarama.NewConsumerGroup(cfg.Brokers, groupID, sc)
	if err != nil {
		return nil, fmt.Errorf("kafka: create consumer group %s: %w", groupID, err)
	}

	logger.L().Info("kafka consumer group created",
		zap.String("group", groupID),
		zap.Strings("topics", topics),
	)

	return &ConsumerGroup{
		group:   group,
		topics:  topics,
		handler: &consumerGroupHandler{fn: handler},
		cfg:     cfg,
	}, nil
}

// Consume starts the consumer loop. Blocks until ctx is cancelled.
// Automatically rejoins on rebalance events.
func (cg *ConsumerGroup) Consume(ctx context.Context) error {
	for {
		if err := cg.group.Consume(ctx, cg.topics, cg.handler); err != nil {
			logger.L().Error("kafka consumer error", zap.Error(err))
		}
		if ctx.Err() != nil {
			return ctx.Err()
		}
	}
}

// Close shuts down the consumer group.
func (cg *ConsumerGroup) Close() error {
	return cg.group.Close()
}

// ── Internal handler adapter ──────────────────────────────────────────────────

type consumerGroupHandler struct {
	fn HandlerFunc
}

func (h *consumerGroupHandler) Setup(_ sarama.ConsumerGroupSession) error   { return nil }
func (h *consumerGroupHandler) Cleanup(_ sarama.ConsumerGroupSession) error { return nil }

func (h *consumerGroupHandler) ConsumeClaim(session sarama.ConsumerGroupSession, claim sarama.ConsumerGroupClaim) error {
	for msg := range claim.Messages() {
		m := Message{
			Topic:     msg.Topic,
			Partition: msg.Partition,
			Offset:    msg.Offset,
			Key:       string(msg.Key),
			Value:     msg.Value,
			Timestamp: msg.Timestamp,
		}

		if err := h.fn(session.Context(), m); err != nil {
			logger.L().Error("message handler error",
				zap.String("topic", msg.Topic),
				zap.Int64("offset", msg.Offset),
				zap.Error(err),
			)
			// Continue processing — do not crash the consumer
		}
		session.MarkMessage(msg, "")
	}
	return nil
}
