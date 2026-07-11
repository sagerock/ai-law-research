ALTER TABLE structured_summary_candidates
    ADD COLUMN IF NOT EXISTS content_hash TEXT,
    ADD COLUMN IF NOT EXISTS generation_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS validation_version TEXT NOT NULL DEFAULT 'v1';

CREATE TABLE IF NOT EXISTS structured_summary_failures (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    content_hash TEXT,
    stage TEXT NOT NULL,
    error TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_structured_summary_failures_case
    ON structured_summary_failures(case_id, provider, created_at DESC);
