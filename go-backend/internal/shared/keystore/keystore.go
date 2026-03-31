// Package keystore provides AES-256-GCM encryption for API keys
// and resolves LLM credentials per user, with fallback to server env vars.
//
// Security model:
//   - Raw API keys are NEVER written to disk or stored in plaintext
//   - Keys are encrypted before DB insert and decrypted in-memory at dispatch time
//   - The KEY_ENCRYPTION_KEY server env var is the root secret (rotate independently of keys)
//   - key_hint (last 4 chars) is the only part safe to surface in the UI
package keystore

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"sync"

	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/secretsmanager"

	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/db"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
	"go.uber.org/zap"
)

// LLMConfig is the resolved config injected into every Kafka TaskMessage.
// The APIKey field is plaintext in RAM only — never serialised to disk.
type LLMConfig struct {
	Provider  string         `json:"provider"` // "openai" | "anthropic" | "google"
	APIKey    string         `json:"api_key"`  // plaintext — in-memory only
	ModelName string         `json:"model"`    // e.g. "gpt-4o"
	Params    map[string]any `json:"params"`   // temperature, max_tokens, etc.
}

// AgentDefaults is the global fallback model config per role.
// These are used when a user has not configured their own preference.
var AgentDefaults = map[string]LLMConfig{
	"CEO": {
		Provider:  "bedrock",
		ModelName: "amazon.nova-pro-v1:0",
	},
	"CTO": {
		Provider:  "bedrock",
		ModelName: "amazon.nova-pro-v1:0",
	},
	"Engineer_Backend": {
		Provider:  "bedrock",
		ModelName: "amazon.nova-lite-v1:0",
	},
	"Engineer_Frontend": {
		Provider:  "bedrock",
		ModelName: "amazon.nova-lite-v1:0",
	},
	"QA": {
		Provider:  "bedrock",
		ModelName: "amazon.nova-lite-v1:0",
	},
	"DevOps": {
		Provider:  "bedrock",
		ModelName: "amazon.nova-lite-v1:0",
	},
	"Finance": {
		Provider:  "bedrock",
		ModelName: "amazon.nova-micro-v1:0",
	},
}

// ── Encryption ────────────────────────────────────────────────────────────────

var (
	cachedMasterKey []byte
	masterKeyOnce   sync.Once
	masterKeyErr    error
)

// masterKey returns the 32-byte AES-256 key.
// Fetches from AWS Secrets Manager, falling back to ENV for local development.
func masterKey() ([]byte, error) {
	masterKeyOnce.Do(func() {
		hexKey := os.Getenv("KEY_ENCRYPTION_KEY")
		// If not in env, attempt AWS Secrets Manager
		if hexKey == "" {
			secretName := os.Getenv("AWS_SECRET_NAME")
			if secretName == "" {
				secretName = "ai-org/key-encryption-key"
			}

			cfg, err := config.LoadDefaultConfig(context.TODO())
			if err == nil {
				client := secretsmanager.NewFromConfig(cfg)
				out, err := client.GetSecretValue(context.TODO(), &secretsmanager.GetSecretValueInput{
					SecretId: &secretName,
				})
				if err == nil && out.SecretString != nil {
					hexKey = *out.SecretString
				}
			}
		}

		if hexKey == "" {
			masterKeyErr = errors.New("KEY_ENCRYPTION_KEY not set in environment or AWS Secrets Manager")
			return
		}

		raw, err := hex.DecodeString(hexKey)
		if err != nil || len(raw) != 32 {
			masterKeyErr = fmt.Errorf("KEY_ENCRYPTION_KEY must be a 64-char hex string (32 bytes): %w", err)
			return
		}
		cachedMasterKey = raw
	})
	return cachedMasterKey, masterKeyErr
}

// Encrypt encrypts plaintext using AES-256-GCM.
// Returns: [12-byte nonce][ciphertext] as a single byte slice.
func Encrypt(plaintext string) ([]byte, error) {
	key, err := masterKey()
	if err != nil {
		return nil, err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return nil, fmt.Errorf("keystore: aes cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return nil, fmt.Errorf("keystore: gcm: %w", err)
	}

	nonce := make([]byte, gcm.NonceSize()) // 12 bytes
	if _, err = io.ReadFull(rand.Reader, nonce); err != nil {
		return nil, fmt.Errorf("keystore: nonce gen: %w", err)
	}

	ciphertext := gcm.Seal(nil, nonce, []byte(plaintext), nil)

	// Prepend nonce so Decrypt can extract it
	result := make([]byte, len(nonce)+len(ciphertext))
	copy(result[:len(nonce)], nonce)
	copy(result[len(nonce):], ciphertext)
	return result, nil
}

// Decrypt decrypts a blob produced by Encrypt.
// Input format: [12-byte nonce][ciphertext]
func Decrypt(blob []byte) (string, error) {
	key, err := masterKey()
	if err != nil {
		return "", err
	}

	block, err := aes.NewCipher(key)
	if err != nil {
		return "", fmt.Errorf("keystore: aes cipher: %w", err)
	}

	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", fmt.Errorf("keystore: gcm: %w", err)
	}

	nonceSize := gcm.NonceSize()
	if len(blob) < nonceSize {
		return "", errors.New("keystore: ciphertext too short")
	}

	nonce, ciphertext := blob[:nonceSize], blob[nonceSize:]
	plaintext, err := gcm.Open(nil, nonce, ciphertext, nil)
	if err != nil {
		return "", fmt.Errorf("keystore: decrypt failed: %w", err)
	}

	return string(plaintext), nil
}

// KeyHint returns only the last 4 characters of an API key.
// Safe to store and display in the UI.
func KeyHint(apiKey string) string {
	if len(apiKey) <= 4 {
		return "****"
	}
	return "..." + apiKey[len(apiKey)-4:]
}

// ── Key Resolution ────────────────────────────────────────────────────────────

// Resolver resolves LLM configs per user and agent role.
type Resolver struct {
	db *db.Pool
}

func NewResolver(pool *db.Pool) *Resolver {
	return &Resolver{db: pool}
}

// ResolveForAgent returns the LLMConfig to use for a given user + agent role.
//
// Resolution order:
//  1. Check agent_model_prefs for (user_id, agent_role) → gives provider + model + key_id
//  2. If key_id set → decrypt that specific user_llm_keys row
//  3. If key_id null → find first valid key for that provider
//  4. If no user keys configured → fall back to server env vars
//  5. If no env var → return default model + empty key (mock/demo mode)
func (r *Resolver) ResolveForAgent(ctx context.Context, userID, agentRole string) LLMConfig {
	log := logger.L().With(zap.String("user_id", userID), zap.String("role", agentRole))

	def := AgentDefaults[agentRole]
	if def.Provider == "" {
		def = LLMConfig{Provider: "bedrock", ModelName: "amazon.nova-pro-v1:0"}
	}

	// 1. Check agent_model_prefs
	type prefRow struct {
		Provider  string
		ModelName string
		KeyID     *string
		Params    map[string]any
	}

	var pref prefRow
	prefQuery := `
		SELECT provider, model_name, key_id::text, model_params
		FROM agent_model_prefs
		WHERE user_id = $1 AND agent_role = $2
		LIMIT 1`

	rows, err := r.db.Query(ctx, prefQuery, userID, agentRole)
	if err != nil {
		log.Warn("agent_model_prefs query failed, using defaults", zap.Error(err))
		return r.resolveEnvFallback(def)
	}
	defer rows.Close()

	hasPref := false
	if rows.Next() {
		hasPref = true
		if err := rows.Scan(&pref.Provider, &pref.ModelName, &pref.KeyID, &pref.Params); err != nil {
			log.Warn("pref row scan failed", zap.Error(err))
			hasPref = false
		}
	}

	if !hasPref {
		// No user preference → use default model, resolve key by provider default
		return r.resolveEnvFallback(def)
	}

	// 2 & 3. Resolve the API key
	apiKey := r.resolveKey(ctx, userID, pref.Provider, pref.KeyID)
	if apiKey == "" {
		// Fall back to server env
		apiKey = serverEnvKey(pref.Provider)
	}

	return LLMConfig{
		Provider:  pref.Provider,
		APIKey:    apiKey,
		ModelName: pref.ModelName,
		Params:    pref.Params,
	}
}

// resolveKey decrypts either a specific key (by key_id) or the first valid key
// for the given user+provider. Returns empty string if none found.
func (r *Resolver) resolveKey(ctx context.Context, userID, provider string, keyID *string) string {
	log := logger.L()

	var query string
	var args []any

	if keyID != nil && *keyID != "" {
		query = `SELECT api_key_enc FROM user_llm_keys WHERE id = $1 AND user_id = $2 AND is_valid = true LIMIT 1`
		args = []any{*keyID, userID}
	} else {
		query = `SELECT api_key_enc FROM user_llm_keys WHERE user_id = $1 AND provider = $2 AND is_valid = true ORDER BY created_at ASC LIMIT 1`
		args = []any{userID, provider}
	}

	rows, err := r.db.Query(ctx, query, args...)
	if err != nil {
		log.Warn("key lookup failed", zap.Error(err))
		return ""
	}
	defer rows.Close()

	if !rows.Next() {
		return ""
	}

	var enc []byte
	if err := rows.Scan(&enc); err != nil {
		return ""
	}

	plain, err := Decrypt(enc)
	if err != nil {
		log.Error("key decrypt failed — marking key invalid", zap.Error(err))
		return ""
	}

	return plain
}

// resolveEnvFallback returns the LLMConfig using the agent's default model
// and the server environment API key for that provider.
func (r *Resolver) resolveEnvFallback(def LLMConfig) LLMConfig {
	def.APIKey = serverEnvKey(def.Provider)
	return def
}

// serverEnvKey returns the server-level API key for the given provider.
// This is the platform owner's key — the final fallback.
func serverEnvKey(provider string) string {
	switch provider {
	case "openai":
		return os.Getenv("OPENAI_API_KEY")
	case "anthropic":
		return os.Getenv("ANTHROPIC_API_KEY")
	case "google":
		return os.Getenv("GOOGLE_API_KEY")
	default:
		return os.Getenv("GOOGLE_API_KEY")
	}
}
