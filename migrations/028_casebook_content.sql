-- 028_casebook_content.sql
-- Full readable text of a casebook, rendered block-by-block for the in-site reader.
-- Populated offline by scripts/build_casebook_reader.py from the source document.
-- para_ordinal matches the "para" field in the casebook's Qdrant collection, so AI
-- Q&A citations can deep-link to the exact paragraph (#para-<n>) in the reader.

CREATE TABLE IF NOT EXISTS casebook_content (
    id            SERIAL PRIMARY KEY,
    casebook_id   INTEGER NOT NULL REFERENCES casebooks(id) ON DELETE CASCADE,
    sort_order    INTEGER NOT NULL,          -- document order across the whole book
    chapter_slug  TEXT    NOT NULL,          -- 'ch4', 'front-license', ...
    chapter_title TEXT    NOT NULL,          -- 'CHAPTER 4.  Character Evidence'
    section       TEXT,                      -- nearest section heading, e.g. '4.2 404(b) Quasi-Exceptions'
    block_type    TEXT    NOT NULL,          -- chapter-title|section|subsection|case|judge|rule|note|problem|quote|diagram|list|table|text|divider
    group_id      INTEGER,                   -- consecutive same-type blocks share this (boxed grouping)
    html          TEXT    NOT NULL,          -- inner HTML of the block
    para_ordinal  INTEGER,                   -- docx paragraph index = Qdrant 'para' (NULL for tables/etc.)
    anchor        TEXT,                       -- 'para-1531' (NULL for non-paragraph blocks)
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_casebook_content_chapter
    ON casebook_content (casebook_id, chapter_slug, sort_order);
CREATE INDEX IF NOT EXISTS idx_casebook_content_para
    ON casebook_content (casebook_id, para_ordinal);
