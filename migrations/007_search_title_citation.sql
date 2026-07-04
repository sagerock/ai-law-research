-- Scope case search to name + citation (drop full-text search over opinion content).
-- This decouples search from `content`, so opinion text can move to R2 without breaking
-- search. Product rationale: students look cases up by name/citation/rule (a lookup), not
-- open-ended research over a partial corpus — which would silently mislead. Real research
-- lives at CourtListener; we link out.

-- Rebuild search_tsv from title only (citations are matched via ILIKE in the query).
CREATE OR REPLACE FUNCTION cases_search_tsv_update() RETURNS trigger AS $$
BEGIN
    NEW.search_tsv := to_tsvector('english', coalesce(NEW.title, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Backfill every existing row to the title-only vector (consistent regardless of whether
-- the opinion text is still in Postgres or has moved to R2).
UPDATE cases SET search_tsv = to_tsvector('english', coalesce(title, ''));
