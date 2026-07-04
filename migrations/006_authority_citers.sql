-- Authority-tier citers (OpenCite phase 1) — precomputed offline by citator/citator_pipeline.py.
-- Each row = one case that cites `target_case_id`, tiered by its binding force relative to that case.
-- Mechanical/index-only: tier comes from court hierarchy, never from AI. See citator/README.md.

CREATE TABLE IF NOT EXISTS case_authority_citers (
    id                SERIAL PRIMARY KEY,
    target_case_id    TEXT NOT NULL,        -- the cited case (= cases.id = CL cluster_id)
    citer_cluster_id  TEXT NOT NULL,        -- the citing case (CL cluster_id)
    citer_name        TEXT,
    citer_court_id    TEXT,
    citer_court_name  TEXT,                 -- short label, e.g. "1st Cir.", "D. Mass.", "N.Y."
    citer_date        DATE,
    tier              TEXT NOT NULL,        -- BINDING-ON-TARGET | SAME-LINE-LOWER |
                                            -- PERSUASIVE-SISTER | SAME-CASE-HISTORY
    run_date          DATE DEFAULT CURRENT_DATE,
    UNIQUE(target_case_id, citer_cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_authority_target ON case_authority_citers(target_case_id);
