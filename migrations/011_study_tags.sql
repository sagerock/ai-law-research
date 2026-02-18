-- Convert study_notes.subject (TEXT) → tags (TEXT[])
-- Existing single subjects become single-element arrays; NULLs stay NULL.

ALTER TABLE study_notes
  ALTER COLUMN subject TYPE TEXT[]
  USING CASE WHEN subject IS NOT NULL THEN ARRAY[subject] ELSE NULL END;

ALTER TABLE study_notes RENAME COLUMN subject TO tags;

CREATE INDEX IF NOT EXISTS idx_study_notes_tags ON study_notes USING GIN (tags);
