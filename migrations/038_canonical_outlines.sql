BEGIN;

-- Canonical outlines are curated public study resources. User-uploaded outlines
-- remain in the legacy tables as private documents for the AI study workflow.
CREATE TABLE IF NOT EXISTS canonical_outlines (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    subject TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    current_version INTEGER NOT NULL DEFAULT 1 CHECK (current_version > 0),
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS canonical_outline_revisions (
    id BIGSERIAL PRIMARY KEY,
    outline_id BIGINT NOT NULL REFERENCES canonical_outlines(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK (version > 0),
    content_hash TEXT NOT NULL,
    revision_note TEXT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (outline_id, version)
);

-- Identity and ordering live here; revision-specific title/body content does not.
CREATE TABLE IF NOT EXISTS canonical_outline_sections (
    id BIGSERIAL PRIMARY KEY,
    outline_id BIGINT NOT NULL REFERENCES canonical_outlines(id) ON DELETE CASCADE,
    section_key TEXT NOT NULL,
    slug TEXT NOT NULL,
    parent_section_id BIGINT REFERENCES canonical_outline_sections(id) ON DELETE RESTRICT,
    sort_order INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (outline_id, section_key),
    UNIQUE (outline_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_canonical_sections_outline_order
    ON canonical_outline_sections(outline_id, sort_order)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS canonical_outline_section_revisions (
    id BIGSERIAL PRIMARY KEY,
    revision_id BIGINT NOT NULL REFERENCES canonical_outline_revisions(id) ON DELETE CASCADE,
    section_id BIGINT NOT NULL REFERENCES canonical_outline_sections(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (revision_id, section_id)
);

CREATE TABLE IF NOT EXISTS canonical_outline_section_sources (
    id BIGSERIAL PRIMARY KEY,
    section_revision_id BIGINT NOT NULL REFERENCES canonical_outline_section_revisions(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL CHECK (target_type IN ('case', 'rule', 'statute', 'constitution', 'other')),
    target_ref TEXT NOT NULL,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (section_revision_id, target_type, target_ref)
);

CREATE TABLE IF NOT EXISTS canonical_outline_section_votes (
    section_id BIGINT NOT NULL REFERENCES canonical_outline_sections(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    vote_type INTEGER NOT NULL CHECK (vote_type IN (-1, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (section_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_canonical_section_votes_section
    ON canonical_outline_section_votes(section_id);

CREATE TABLE IF NOT EXISTS canonical_outline_section_comments (
    id BIGSERIAL PRIMARY KEY,
    section_id BIGINT NOT NULL REFERENCES canonical_outline_sections(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    author_name TEXT,
    content TEXT NOT NULL CHECK (char_length(btrim(content)) > 0),
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_canonical_section_comments_section_created
    ON canonical_outline_section_comments(section_id, created_at);
CREATE INDEX IF NOT EXISTS idx_canonical_section_comments_unresolved
    ON canonical_outline_section_comments(section_id)
    WHERE resolved_at IS NULL;

-- Repair fresh-schema drift in the retained private-upload feature.
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS show_author BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS show_school BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE outlines ALTER COLUMN file_url DROP NOT NULL;

-- The public upload marketplace is retired; preserve every file and conversation privately.
UPDATE outlines SET visibility = 'private', is_public = FALSE
WHERE visibility <> 'private' OR is_public = TRUE;

COMMIT;
