-- Add AI summaries table to cache generated case briefs
CREATE TABLE IF NOT EXISTS ai_summaries (
    id SERIAL PRIMARY KEY,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    summary TEXT NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(case_id)  -- One summary per case
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_ai_summaries_case_id ON ai_summaries(case_id);

-- Add a column to track when summaries were generated
COMMENT ON TABLE ai_summaries IS 'Cached AI-generated case brief summaries';
COMMENT ON COLUMN ai_summaries.model IS 'AI model used (e.g., gpt-5-mini)';
COMMENT ON COLUMN ai_summaries.cost IS 'Cost in USD to generate this summary';
