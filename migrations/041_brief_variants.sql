BEGIN;

-- Simplified and bullet-point versions of a case's approved source-linked brief.
-- A variant is a rewrite of that brief, not of the opinion; source_digest fingerprints
-- the detailed brief it was written from, so a regenerated brief makes the variant
-- stale instead of silently mismatched. Lines carry passage sources derived from the
-- detailed claims they rewrite (backend/brief_variants.py).
CREATE TABLE IF NOT EXISTS brief_variants (
    case_id TEXT PRIMARY KEY REFERENCES cases(id) ON DELETE CASCADE,
    source_provider TEXT NOT NULL,
    source_digest TEXT NOT NULL,
    simplified JSONB NOT NULL,
    bullets JSONB NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    cost NUMERIC(10, 6) NOT NULL DEFAULT 0,
    key_source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Served only through FastAPI; keep the Supabase API roles default-denied (see 037).
ALTER TABLE public.brief_variants ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    api_role TEXT;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON TABLE public.brief_variants FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$;

COMMIT;
