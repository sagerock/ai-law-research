BEGIN;

-- Doctrine topic tags for cases. Tags may only come from a curated per-subject taxonomy
-- (data/topics/<subject>.json), never free-form, so near-duplicate tags cannot sprawl.
-- Doctrine ids are namespaced by subject ("con-law:ripeness") because slugs like
-- "takings" would otherwise collide across subjects.
CREATE TABLE IF NOT EXISTS topic_doctrines (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL,
    label TEXT NOT NULL,
    topic_rank INTEGER NOT NULL,
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS case_topics (
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    doctrine_id TEXT NOT NULL REFERENCES topic_doctrines(id) ON UPDATE CASCADE,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    confidence TEXT CHECK (confidence IN ('high', 'medium', 'low')),
    rationale TEXT,
    source TEXT NOT NULL DEFAULT 'ai',
    model TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, doctrine_id)
);

CREATE INDEX IF NOT EXISTS idx_case_topics_doctrine ON case_topics (doctrine_id);

-- Served only through FastAPI; keep the Supabase API roles default-denied (see 037).
ALTER TABLE public.topic_doctrines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.case_topics ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    api_role TEXT;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON TABLE public.topic_doctrines, public.case_topics FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$;

COMMIT;
