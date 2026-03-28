-- Track citation URL 404s for monitoring
CREATE TABLE IF NOT EXISTS citation_404s (
    slug TEXT PRIMARY KEY,
    hit_count INTEGER NOT NULL DEFAULT 1,
    first_seen TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_citation_404s_hits ON citation_404s (hit_count DESC);
