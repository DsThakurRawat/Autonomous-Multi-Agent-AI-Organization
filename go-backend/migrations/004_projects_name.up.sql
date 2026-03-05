-- Migration 004: Add name column to projects
-- The dashboard shows project.name in the sidebar.
-- We use idea as the default name (first 80 chars) on back-fill.

BEGIN;

ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS name TEXT;

-- Back-fill: use first 80 chars of idea as name for existing rows
UPDATE projects
SET name = LEFT(idea, 80)
WHERE name IS NULL;

-- Make name required going forward
ALTER TABLE projects
    ALTER COLUMN name SET NOT NULL,
    ALTER COLUMN name SET DEFAULT '';

COMMIT;
