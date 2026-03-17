package crypto

import (
	"fmt"
	"os"
	"path/filepath"

	"go.uber.org/zap"
	"github.com/DsThakurRawat/autonomous-org/go-backend/internal/shared/logger"
)

// SecretManager handles writing sensitive credentials to ephemeral storage (tmpfs).
type SecretManager struct {
	basePath string
}

// NewSecretManager creates a new SecretManager targeting the given base directory.
func NewSecretManager(basePath string) *SecretManager {
	return &SecretManager{
		basePath: basePath,
	}
}

// WriteSecret writes a secret to a file in the managed directory.
// The file is created with restrictive permissions (0600).
func (s *SecretManager) WriteSecret(name string, value string) error {
	if s.basePath == "" {
		return fmt.Errorf("secret_manager: base path not set")
	}

	// Ensure target directory exists
	if err := os.MkdirAll(s.basePath, 0700); err != nil && !os.IsExist(err) {
		return fmt.Errorf("secret_manager: failed to create base dir: %w", err)
	}

	secretPath := filepath.Join(s.basePath, name)
	
	// Write with 0600 (read/write for owner only)
	err := os.WriteFile(secretPath, []byte(value), 0600)
	if err != nil {
		return fmt.Errorf("secret_manager: failed to write secret %s: %w", name, err)
	}

	logger.L().Debug("secret written to tmpfs", zap.String("name", name), zap.String("path", secretPath))
	return nil
}

// RemoveSecret deletes a secret file.
func (s *SecretManager) RemoveSecret(name string) error {
	secretPath := filepath.Join(s.basePath, name)
	if err := os.Remove(secretPath); err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("secret_manager: failed to remove secret %s: %w", name, err)
	}
	return nil
}

// ClearAll removes all secrets in the base directory.
func (s *SecretManager) ClearAll() error {
	entries, err := os.ReadDir(s.basePath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			_ = s.RemoveSecret(entry.Name())
		}
	}
	return nil
}
