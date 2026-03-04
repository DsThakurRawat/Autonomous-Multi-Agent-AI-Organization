-- Migration 001: Initial schema
-- Creates the core tables for the AI Organization system.
-- Run with: migrate -path migrations -database "$DATABASE_URL" up

BEGIN;

-- ── Extensions ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- For gen_random_uuid()

-- ── Tenants ───────────────────────────────────────────────────────────────────
CREATE TABLE tenants (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name           TEXT        NOT NULL,
    plan           TEXT        NOT NULL DEFAULT 'free'  CHECK (plan IN ('free', 'pro', 'enterprise')),
    max_projects   INT         NOT NULL DEFAULT 3,
    max_tokens_mo  BIGINT      NOT NULL DEFAULT 1000000,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE users (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    google_sub   TEXT        UNIQUE,   -- NULL until Google OAuth login
    email        TEXT        NOT NULL UNIQUE,
    display_name TEXT,
    role         TEXT        NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login   TIMESTAMPTZ
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL;

-- ── Projects ──────────────────────────────────────────────────────────────────
CREATE TABLE projects (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id      UUID        NOT NULL REFERENCES users(id),
    idea         TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','planning','running','done','failed','cancelled')),
    budget_usd   NUMERIC(10,4),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_projects_tenant  ON projects(tenant_id, status);
CREATE INDEX idx_projects_user    ON projects(user_id);
CREATE INDEX idx_projects_status  ON projects(status) WHERE status IN ('pending','planning','running');

-- ── Tasks (DAG nodes) ─────────────────────────────────────────────────────────
CREATE TABLE tasks (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name         TEXT        NOT NULL,
    task_type    TEXT        NOT NULL,
    agent_role   TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending','running','done','failed','skipped')),
    input_data   JSONB       NOT NULL DEFAULT '{}',
    output_data  JSONB,
    error_msg    TEXT,
    retry_count  INT         NOT NULL DEFAULT 0,
    max_retries  INT         NOT NULL DEFAULT 3,
    duration_ms  INT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_tasks_project    ON tasks(project_id);
CREATE INDEX idx_tasks_status     ON tasks(status) WHERE status IN ('pending','running');
CREATE INDEX idx_tasks_agent_role ON tasks(agent_role);

-- ── Task Dependencies (DAG edges) ─────────────────────────────────────────────
CREATE TABLE task_dependencies (
    task_id    UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, depends_on),
    CHECK (task_id != depends_on)   -- No self-loops
);

-- ── Cost / Token Ledger ───────────────────────────────────────────────────────
CREATE TABLE cost_events (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    task_id     UUID        REFERENCES tasks(id),
    agent_role  TEXT        NOT NULL,
    model_used  TEXT        NOT NULL,
    tokens_in   INT         NOT NULL DEFAULT 0,
    tokens_out  INT         NOT NULL DEFAULT 0,
    cost_usd    NUMERIC(10,6) NOT NULL DEFAULT 0,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cost_project     ON cost_events(project_id, recorded_at DESC);
CREATE INDEX idx_cost_tenant      ON cost_events(project_id);  -- Join via projects
CREATE INDEX idx_cost_monthly     ON cost_events(recorded_at);  -- For monthly aggregation

-- ── Agent Heartbeats ──────────────────────────────────────────────────────────
CREATE TABLE agent_heartbeats (
    agent_role   TEXT        NOT NULL,
    pod_id       TEXT        NOT NULL,
    last_seen    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status       TEXT        NOT NULL DEFAULT 'healthy',
    PRIMARY KEY (agent_role, pod_id)
);

-- ── Updated-at trigger ────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tenants_updated_at   BEFORE UPDATE ON tenants   FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_projects_updated_at  BEFORE UPDATE ON projects  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

COMMIT;
