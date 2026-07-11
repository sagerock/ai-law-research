-- Keep citation-aware candidates alongside the original prose summary for A/B review.
ALTER TABLE ai_summaries
    ADD COLUMN IF NOT EXISTS structured_summary JSONB,
    ADD COLUMN IF NOT EXISTS structured_model TEXT,
    ADD COLUMN IF NOT EXISTS structured_created_at TIMESTAMP;
