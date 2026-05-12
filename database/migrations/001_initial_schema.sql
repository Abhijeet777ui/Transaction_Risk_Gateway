-- ============================================================
-- Migration 001: Initial Schema
-- Transaction Risk Gateway - PostgreSQL
-- ============================================================

-- Users table: stores behavioral profile per user
CREATE TABLE IF NOT EXISTS users (
    id                  VARCHAR(255) PRIMARY KEY,
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    residence_country   VARCHAR(2)   NOT NULL DEFAULT 'XX',
    known_recipients    JSONB        NOT NULL DEFAULT '[]',
    known_countries     JSONB        NOT NULL DEFAULT '[]',
    transaction_history JSONB        NOT NULL DEFAULT '[]',
    failed_attempts     INTEGER      NOT NULL DEFAULT 0,
    account_locked_until TIMESTAMP   NULL
);

CREATE INDEX IF NOT EXISTS idx_users_country ON users(residence_country);
CREATE INDEX IF NOT EXISTS idx_users_locked  ON users(account_locked_until)
    WHERE account_locked_until IS NOT NULL;

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- Audit logs: full immutable record of every decision
-- NOTE: For production at scale, partition by RANGE(timestamp).
--       For now, plain table with good indexes is sufficient.
CREATE TABLE IF NOT EXISTS audit_logs (
    id                  BIGSERIAL    PRIMARY KEY,
    transaction_id      VARCHAR(255) UNIQUE NOT NULL,
    user_id             VARCHAR(255) NOT NULL REFERENCES users(id),
    timestamp           TIMESTAMP    NOT NULL,
    transaction         JSONB        NOT NULL,
    signals             JSONB        NOT NULL,
    decision            VARCHAR(50)  NOT NULL,
    combined_risk_score DECIMAL(5,4) NOT NULL,
    required_actions    JSONB        NOT NULL DEFAULT '[]',
    reasoning           TEXT         NOT NULL,
    human_decision      VARCHAR(50)  NULL,
    reviewer_id         VARCHAR(255) NULL,
    appeal_status       VARCHAR(50)  NULL,
    system_version      VARCHAR(20)  NOT NULL DEFAULT '2.0.0',
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_user_time  ON audit_logs(user_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_decision   ON audit_logs(decision);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp  ON audit_logs(timestamp DESC);
