-- Migration 003: User auth improvements
-- Adds updated_at to users for ON CONFLICT DO UPDATE tracking.
-- Adds a function to auto-provision a personal tenant on first Google login.
-- This is required by the OAuth callback upsertUser logic.

BEGIN;

-- ── 1. Add updated_at to users ────────────────────────────────────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Backfill existing rows
UPDATE users SET updated_at = created_at WHERE updated_at = NOW();

-- Trigger to auto-update the column
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ── 2. Function: get_or_create_personal_tenant ────────────────────────────────
-- Creates a personal "free" tenant for the user on first login.
-- Called from upsert_google_user() below.
-- Safe to call multiple times — uses ON CONFLICT DO NOTHING.
CREATE OR REPLACE FUNCTION get_or_create_personal_tenant(p_email TEXT)
RETURNS UUID AS $$
DECLARE
    v_tenant_id UUID;
BEGIN
    -- Find existing personal tenant for this email
    SELECT t.id INTO v_tenant_id
    FROM tenants t
    WHERE t.name = 'personal:' || p_email
    LIMIT 1;

    IF v_tenant_id IS NULL THEN
        INSERT INTO tenants (name, plan, max_projects, max_tokens_mo)
        VALUES ('personal:' || p_email, 'free', 3, 1000000)
        RETURNING id INTO v_tenant_id;
    END IF;

    RETURN v_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- ── 3. Function: upsert_google_user ───────────────────────────────────────────
-- Called by Go OAuth callback. Atomically:
--   a) Gets or creates a personal tenant
--   b) Upserts the user by google_sub
-- Returns (user_id, tenant_id) so the caller can issue a JWT immediately.
--
-- Why a function instead of inline SQL:
--   Avoids a race condition between checking for the tenant and inserting.
--   The entire operation is one round-trip from Go.
CREATE OR REPLACE FUNCTION upsert_google_user(
    p_google_sub  TEXT,
    p_email       TEXT,
    p_display_name TEXT
)
RETURNS TABLE(user_id UUID, tenant_id UUID) AS $$
DECLARE
    v_tenant_id UUID;
    v_user_id   UUID;
BEGIN
    -- Step 1: ensure personal tenant exists
    v_tenant_id := get_or_create_personal_tenant(p_email);

    -- Step 2: upsert user
    INSERT INTO users (google_sub, email, display_name, tenant_id)
    VALUES (p_google_sub, p_email, p_display_name, v_tenant_id)
    ON CONFLICT (google_sub) DO UPDATE
        SET email        = EXCLUDED.email,
            display_name = EXCLUDED.display_name,
            updated_at   = NOW(),
            last_login   = NOW()
    RETURNING id INTO v_user_id;

    RETURN QUERY SELECT v_user_id, v_tenant_id;
END;
$$ LANGUAGE plpgsql;

-- ── 4. Index: speed up OAuth email lookups ────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

COMMIT;
