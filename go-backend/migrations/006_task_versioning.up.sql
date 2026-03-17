-- Migration 006: Add versioning to tasks
-- Enables optimistic locking for idempotent result processing.

BEGIN;

ALTER TABLE tasks ADD COLUMN version INT NOT NULL DEFAULT 1;

COMMIT;
