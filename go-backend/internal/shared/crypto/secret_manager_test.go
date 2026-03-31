package crypto

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestWriteSecret_CreatesFile(t *testing.T) {
	dir := t.TempDir()
	sm := NewSecretManager(dir)

	err := sm.WriteSecret("API_KEY", "sk-1234567890abcdef")
	require.NoError(t, err)

	data, err := os.ReadFile(filepath.Join(dir, "API_KEY"))
	require.NoError(t, err)
	assert.Equal(t, "sk-1234567890abcdef", string(data))
}

func TestWriteSecret_RestrictivePermissions(t *testing.T) {
	dir := t.TempDir()
	sm := NewSecretManager(dir)
	_ = sm.WriteSecret("CREDENTIAL", "secret-value")

	info, err := os.Stat(filepath.Join(dir, "CREDENTIAL"))
	require.NoError(t, err)
	assert.Equal(t, os.FileMode(0600), info.Mode().Perm())
}

func TestWriteSecret_EmptyBasePath(t *testing.T) {
	sm := NewSecretManager("")
	err := sm.WriteSecret("KEY", "value")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "base path not set")
}

func TestWriteSecret_CreatesNestedDirs(t *testing.T) {
	dir := t.TempDir()
	nestedPath := filepath.Join(dir, "secrets", "ai-org")
	sm := NewSecretManager(nestedPath)

	err := sm.WriteSecret("DB_PASSWORD", "pg_pass_123")
	require.NoError(t, err)

	data, _ := os.ReadFile(filepath.Join(nestedPath, "DB_PASSWORD"))
	assert.Equal(t, "pg_pass_123", string(data))
}

func TestRemoveSecret(t *testing.T) {
	dir := t.TempDir()
	sm := NewSecretManager(dir)
	_ = sm.WriteSecret("TEMP_KEY", "temp_value")

	err := sm.RemoveSecret("TEMP_KEY")
	require.NoError(t, err)
	_, err = os.Stat(filepath.Join(dir, "TEMP_KEY"))
	assert.True(t, os.IsNotExist(err))
}

func TestRemoveSecret_Nonexistent(t *testing.T) {
	dir := t.TempDir()
	sm := NewSecretManager(dir)
	err := sm.RemoveSecret("NONEXISTENT")
	assert.NoError(t, err) // Should not error on missing file
}

func TestClearAll(t *testing.T) {
	dir := t.TempDir()
	sm := NewSecretManager(dir)
	_ = sm.WriteSecret("KEY_1", "value1")
	_ = sm.WriteSecret("KEY_2", "value2")
	_ = sm.WriteSecret("KEY_3", "value3")

	err := sm.ClearAll()
	require.NoError(t, err)

	entries, _ := os.ReadDir(dir)
	assert.Empty(t, entries)
}

func TestClearAll_EmptyDir(t *testing.T) {
	dir := t.TempDir()
	sm := NewSecretManager(dir)
	err := sm.ClearAll()
	assert.NoError(t, err)
}

func TestClearAll_NonexistentDir(t *testing.T) {
	sm := NewSecretManager("/tmp/nonexistent-secret-dir-test-42")
	err := sm.ClearAll()
	assert.NoError(t, err) // Should handle gracefully
}

func TestWriteSecret_OverwritesExisting(t *testing.T) {
	dir := t.TempDir()
	sm := NewSecretManager(dir)
	_ = sm.WriteSecret("ROTATE_KEY", "old-secret")
	_ = sm.WriteSecret("ROTATE_KEY", "new-secret")

	data, _ := os.ReadFile(filepath.Join(dir, "ROTATE_KEY"))
	assert.Equal(t, "new-secret", string(data))
}
