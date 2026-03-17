-- Migration 006: Undo task versioning
BEGIN;

ALTER TABLE tasks DROP COLUMN version;

COMMIT;
