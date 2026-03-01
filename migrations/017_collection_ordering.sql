-- Migration 017: Add position column for drag-and-drop reordering of collection items

-- Add position column to both tables
ALTER TABLE collection_cases ADD COLUMN IF NOT EXISTS position INTEGER DEFAULT 0;
ALTER TABLE collection_legal_texts ADD COLUMN IF NOT EXISTS position INTEGER DEFAULT 0;

-- Backfill positions: rank all items per collection across both tables by added_at DESC
-- Items are interleaved so cases and legal_texts share a unified position space
WITH unified AS (
    SELECT 'case' as item_type, id, collection_id, added_at
    FROM collection_cases
    UNION ALL
    SELECT 'legal_text' as item_type, id, collection_id, added_at
    FROM collection_legal_texts
),
ranked AS (
    SELECT item_type, id, collection_id,
           ROW_NUMBER() OVER (PARTITION BY collection_id ORDER BY added_at DESC) - 1 AS pos
    FROM unified
)
UPDATE collection_cases cc
SET position = r.pos
FROM ranked r
WHERE r.item_type = 'case' AND r.id = cc.id;

WITH unified AS (
    SELECT 'case' as item_type, id, collection_id, added_at
    FROM collection_cases
    UNION ALL
    SELECT 'legal_text' as item_type, id, collection_id, added_at
    FROM collection_legal_texts
),
ranked AS (
    SELECT item_type, id, collection_id,
           ROW_NUMBER() OVER (PARTITION BY collection_id ORDER BY added_at DESC) - 1 AS pos
    FROM unified
)
UPDATE collection_legal_texts clt
SET position = r.pos
FROM ranked r
WHERE r.item_type = 'legal_text' AND r.id = clt.id;

-- Add composite indexes for fast ORDER BY
CREATE INDEX IF NOT EXISTS idx_collection_cases_position ON collection_cases (collection_id, position);
CREATE INDEX IF NOT EXISTS idx_collection_legal_texts_position ON collection_legal_texts (collection_id, position);
