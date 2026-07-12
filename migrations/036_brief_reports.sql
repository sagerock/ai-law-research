CREATE TABLE IF NOT EXISTS brief_reports (
    id BIGSERIAL PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    summary_version TEXT NOT NULL,
    note TEXT,
    user_id TEXT,
    reporter_fingerprint TEXT,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CHECK (user_id IS NOT NULL OR reporter_fingerprint IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_brief_reports_unresolved
    ON brief_reports(resolved, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_brief_reports_fingerprint
    ON brief_reports(reporter_fingerprint, created_at DESC)
    WHERE reporter_fingerprint IS NOT NULL;
