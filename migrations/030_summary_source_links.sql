-- Stable, content-derived opinion passages and source links for AI brief sections.
CREATE TABLE IF NOT EXISTS opinion_passages (
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL,
    passage_id TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    opinion_part TEXT NOT NULL DEFAULT 'opinion',
    text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, content_hash, passage_id),
    UNIQUE (case_id, content_hash, ordinal)
);

CREATE TABLE IF NOT EXISTS summary_source_links (
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    passage_id TEXT NOT NULL,
    confidence DECIMAL(5, 4),
    method TEXT NOT NULL DEFAULT 'deterministic',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, section_key, content_hash, passage_id),
    FOREIGN KEY (case_id, content_hash, passage_id)
        REFERENCES opinion_passages(case_id, content_hash, passage_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_summary_source_links_case
    ON summary_source_links(case_id, content_hash, section_key);
