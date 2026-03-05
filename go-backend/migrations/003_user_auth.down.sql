-- Migration 003: Rollback
BEGIN;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
DROP FUNCTION IF EXISTS upsert_google_user(TEXT, TEXT, TEXT);
DROP FUNCTION IF EXISTS get_or_create_personal_tenant(TEXT);
DROP INDEX  IF EXISTS idx_users_email;
ALTER TABLE users DROP COLUMN IF EXISTS updated_at;

COMMIT;
