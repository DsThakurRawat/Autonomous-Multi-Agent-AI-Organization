-- ═══════════════════════════════════════════════════════════════
-- AI Organization — PostgreSQL Schema
-- Auto-run on first container start
-- ═══════════════════════════════════════════════════════════════

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- For text search

-- ── Projects ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    budget_usd      DECIMAL(12,4),
    spent_usd       DECIMAL(12,4) DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

-- ── Tasks ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    agent_role      VARCHAR(100) NOT NULL,
    task_type       VARCHAR(100),
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    priority        INTEGER DEFAULT 5,
    input_data      JSONB,
    output_data     JSONB,
    error_message   TEXT,
    retry_count     INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_ms     BIGINT,
    cost_usd        DECIMAL(12,6) DEFAULT 0,
    tokens_used     INTEGER DEFAULT 0,
    trace_id        VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Decision Log ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES tasks(id) ON DELETE SET NULL,
    agent_role      VARCHAR(100) NOT NULL,
    decision_type   VARCHAR(100) NOT NULL,
    rationale       TEXT,
    alternatives    JSONB,
    selected        VARCHAR(500),
    confidence      DECIMAL(5,4),
    trace_id        VARCHAR(64),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Cost Ledger ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cost_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES tasks(id) ON DELETE SET NULL,
    agent_role      VARCHAR(100),
    cost_type       VARCHAR(50) NOT NULL,   -- llm | aws | tool
    provider        VARCHAR(100),
    model           VARCHAR(100),
    amount_usd      DECIMAL(12,6) NOT NULL,
    tokens_input    INTEGER DEFAULT 0,
    tokens_output   INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── MoE Routing History ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS moe_routing_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id         VARCHAR(64),
    project_id      VARCHAR(64),
    task_type       VARCHAR(100),
    selected_expert VARCHAR(100),
    routing_type    VARCHAR(50),
    score           DECIMAL(6,4),
    confidence      DECIMAL(5,4),
    latency_ms      DECIMAL(10,2),
    alternatives    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Artifacts ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES tasks(id) ON DELETE SET NULL,
    name            VARCHAR(255) NOT NULL,
    artifact_type   VARCHAR(100),   -- code | config | report | docker | terraform
    content         TEXT,
    file_path       VARCHAR(500),
    checksum        VARCHAR(64),
    size_bytes      BIGINT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Indexes ───────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent_role ON tasks(agent_role);
CREATE INDEX IF NOT EXISTS idx_decisions_project_id ON decisions(project_id);
CREATE INDEX IF NOT EXISTS idx_cost_entries_project_id ON cost_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_moe_log_task_type ON moe_routing_log(task_type);
CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);

-- ── Updated_at trigger ────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

SELECT 'AI Organization schema initialized successfully' AS status;
