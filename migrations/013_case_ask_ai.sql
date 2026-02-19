-- Add optional case_id to conversations for "Ask AI" on case pages
-- Study chat conversations have case_id IS NULL; case chats have it set.

ALTER TABLE conversations ADD COLUMN IF NOT EXISTS case_id TEXT;
CREATE INDEX IF NOT EXISTS idx_conversations_case_id ON conversations(case_id);
