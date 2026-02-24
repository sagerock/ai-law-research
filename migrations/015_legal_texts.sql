-- Legal texts: Constitution, FRCP, Federal Statutes
-- Documents hold metadata; items hold searchable top-level entries with full nested content as JSONB

CREATE TABLE IF NOT EXISTS legal_documents (
    id TEXT PRIMARY KEY,              -- 'constitution', 'frcp', 'federal_statutes'
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,           -- same as id, for filtering
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS legal_text_items (
    id SERIAL PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES legal_documents(id) ON DELETE CASCADE,
    slug TEXT NOT NULL,                -- 'rule-12', 'amendment-14', '28-usc-1332'
    title TEXT NOT NULL,
    citation TEXT,                     -- '28 U.S.C. § 1332' (statutes only)
    number TEXT,                       -- '12', '4.1', 'A', 'XIV' (rules/amendments)
    body TEXT,                         -- all text flattened for full-text search
    content JSONB NOT NULL,            -- full nested structure for rendering
    sort_order INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(document_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_legal_items_document ON legal_text_items(document_id);
CREATE INDEX IF NOT EXISTS idx_legal_items_slug ON legal_text_items(slug);
CREATE INDEX IF NOT EXISTS idx_legal_items_body_fts ON legal_text_items USING gin(to_tsvector('english', body));
