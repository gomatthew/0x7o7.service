BEGIN;

ALTER TABLE "user" ALTER COLUMN password DROP NOT NULL;
ALTER TABLE "user" ALTER COLUMN mail TYPE VARCHAR(254);
CREATE UNIQUE INDEX IF NOT EXISTS uq_user_mail_normalized ON "user" (lower(mail)) WHERE mail IS NOT NULL;

CREATE TABLE IF NOT EXISTS demo_sessions (
    id VARCHAR(64) PRIMARY KEY, user_id VARCHAR(64) NOT NULL, knowledge_base_id VARCHAR(64) NOT NULL UNIQUE,
    original_filename VARCHAR(256) NOT NULL, storage_path VARCHAR(512) NOT NULL, file_type VARCHAR(16) NOT NULL,
    page_count INTEGER NOT NULL DEFAULT 0, character_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(24) NOT NULL DEFAULT 'ready', expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_demo_sessions_user_id ON demo_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_demo_sessions_expires_at ON demo_sessions(expires_at);

CREATE TABLE IF NOT EXISTS demo_jobs (
    id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64), user_id VARCHAR(64), analysis_type VARCHAR(64) NOT NULL,
    status VARCHAR(24) NOT NULL DEFAULT 'running', result JSON, sources JSON, error_code VARCHAR(64),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(), finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS leads (
    id VARCHAR(64) PRIMARY KEY, name VARCHAR(120) NOT NULL, work_email VARCHAR(254) NOT NULL,
    company VARCHAR(180) NOT NULL, website VARCHAR(512), project_type VARCHAR(80) NOT NULL,
    project_summary TEXT NOT NULL, timeline VARCHAR(80) NOT NULL, budget_range VARCHAR(80),
    contact_consent BOOLEAN NOT NULL DEFAULT FALSE, source_page VARCHAR(512),
    status VARCHAR(24) NOT NULL DEFAULT 'new', created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS ix_leads_work_email ON leads(work_email);

CREATE TABLE IF NOT EXISTS demo_events (
    id VARCHAR(64) PRIMARY KEY, session_id VARCHAR(64), user_id VARCHAR(64), event_type VARCHAR(64) NOT NULL,
    status VARCHAR(24) NOT NULL, duration_ms INTEGER, properties JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_demo_events_event_type ON demo_events(event_type);

COMMIT;
