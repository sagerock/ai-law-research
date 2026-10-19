BEGIN;

-- "Request this brief" (Sage, 2026-10-19). Visitors get no live AI generation; a
-- signed-in reader asks for a missing brief instead, and the desktop subscription
-- pipeline works the cases in demand order. One row per reader per case, so a
-- repeat click is a no-op and the request count is the demand. A request is
-- fulfilled once the case has an approved source-linked brief; nothing here
-- tracks that, the queue query derives it.
CREATE TABLE IF NOT EXISTS brief_requests (
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (case_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_brief_requests_user_created
    ON brief_requests (user_id, created_at);

-- Served only through FastAPI; keep the Supabase API roles default-denied (see 037).
ALTER TABLE public.brief_requests ENABLE ROW LEVEL SECURITY;

DO $$
DECLARE
    api_role TEXT;
BEGIN
    FOREACH api_role IN ARRAY ARRAY['anon', 'authenticated']
    LOOP
        IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = api_role) THEN
            EXECUTE format(
                'REVOKE ALL PRIVILEGES ON TABLE public.brief_requests FROM %I',
                api_role
            );
        END IF;
    END LOOP;
END
$$;

COMMIT;
