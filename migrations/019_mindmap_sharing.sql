-- 019_mindmap_sharing.sql
-- Add sharing, subject tagging, and updated_at to mindmaps

ALTER TABLE mindmaps ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT false;
ALTER TABLE mindmaps ADD COLUMN IF NOT EXISTS subject TEXT;
ALTER TABLE mindmaps ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();
CREATE INDEX IF NOT EXISTS idx_mindmaps_public ON mindmaps(is_public) WHERE is_public = true;
