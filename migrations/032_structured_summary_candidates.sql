-- Store multiple source-linked candidates without replacing the original brief.
CREATE TABLE IF NOT EXISTS structured_summary_candidates (
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    summary JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, provider)
);

INSERT INTO structured_summary_candidates (case_id, provider, model, summary, created_at)
SELECT case_id, 'claude', structured_model, structured_summary,
       COALESCE(structured_created_at, NOW())
FROM ai_summaries
WHERE structured_summary IS NOT NULL AND structured_model IS NOT NULL
ON CONFLICT (case_id, provider) DO NOTHING;
