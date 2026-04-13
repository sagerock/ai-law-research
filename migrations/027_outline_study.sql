-- migrations/027_outline_study.sql
-- Extend outlines with visibility, text content, forking; add outline study conversations

-- Replace is_public boolean with visibility text field
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS visibility TEXT NOT NULL DEFAULT 'private';

-- Migrate existing data: is_public=true -> 'public', is_public=false -> 'private'
UPDATE outlines SET visibility = CASE WHEN is_public = TRUE THEN 'public' ELSE 'private' END;

-- Add extracted text content for AI features
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS content TEXT;

-- Add forking support
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS forked_from INTEGER REFERENCES outlines(id) ON DELETE SET NULL;
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS fork_count INTEGER NOT NULL DEFAULT 0;

-- Add year column for course year metadata
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS year INTEGER;

-- AI-extracted topics from outline content
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS topics JSONB;

-- Store original file in database for direct upload/download
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS original_file BYTEA;
ALTER TABLE outlines ADD COLUMN IF NOT EXISTS original_content_type TEXT;

-- Update indexes for visibility-based queries
DROP INDEX IF EXISTS idx_outlines_public;
CREATE INDEX IF NOT EXISTS idx_outlines_visibility_subject ON outlines(visibility, subject);
CREATE INDEX IF NOT EXISTS idx_outlines_forked_from ON outlines(forked_from) WHERE forked_from IS NOT NULL;

-- Outline study conversations (separate from general study_notes conversations)
CREATE TABLE IF NOT EXISTS outline_conversations (
    id SERIAL PRIMARY KEY,
    outline_id INTEGER NOT NULL REFERENCES outlines(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    mode TEXT NOT NULL,  -- 'multiple_choice' or 'practice_essay'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_outline_conv_outline_user ON outline_conversations(outline_id, user_id);

-- Messages for outline study conversations
CREATE TABLE IF NOT EXISTS outline_conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES outline_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,  -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_outline_msgs_conv ON outline_conversation_messages(conversation_id);
