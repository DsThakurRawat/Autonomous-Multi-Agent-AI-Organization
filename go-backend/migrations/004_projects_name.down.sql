-- Migration 004: Rollback
BEGIN;
ALTER TABLE projects DROP COLUMN IF EXISTS name;
COMMIT;
