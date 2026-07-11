CREATE TABLE IF NOT EXISTS brief_preferences (
    user_id TEXT NOT NULL,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    preferred_version TEXT NOT NULL CHECK (preferred_version IN ('claude', 'openai', 'original', 'no_preference')),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, case_id)
);

CREATE TABLE IF NOT EXISTS brief_interactions (
    id BIGSERIAL PRIMARY KEY,
    user_id TEXT,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('source_click', 'tab_select')),
    version TEXT NOT NULL,
    passage_id TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_brief_preferences_case ON brief_preferences(case_id);
CREATE INDEX IF NOT EXISTS idx_brief_interactions_case ON brief_interactions(case_id, event_type, created_at DESC);
