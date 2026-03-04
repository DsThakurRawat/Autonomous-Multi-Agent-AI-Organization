-- Rollback migration 001
BEGIN;
DROP TABLE IF EXISTS agent_heartbeats   CASCADE;
DROP TABLE IF EXISTS cost_events        CASCADE;
DROP TABLE IF EXISTS task_dependencies  CASCADE;
DROP TABLE IF EXISTS tasks              CASCADE;
DROP TABLE IF EXISTS projects           CASCADE;
DROP TABLE IF EXISTS users              CASCADE;
DROP TABLE IF EXISTS tenants            CASCADE;
DROP FUNCTION IF EXISTS set_updated_at CASCADE;
COMMIT;
