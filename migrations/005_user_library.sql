-- User library features: profiles, bookmarks, and collection improvements
-- Run this on Railway PostgreSQL

-- User profiles table (stores display names for authenticated users)
CREATE TABLE IF NOT EXISTS profiles (
    id TEXT PRIMARY KEY,  -- Supabase UUID stored as text
    username TEXT UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    bio TEXT,
    reputation INTEGER DEFAULT 0,
    law_school TEXT,
    graduation_year INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Bookmarks table for saving individual cases
CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,  -- Supabase UUID stored as text
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    folder TEXT DEFAULT 'default',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, case_id)
);

-- Add subject column to collections if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'collections' AND column_name = 'subject'
    ) THEN
        ALTER TABLE collections ADD COLUMN subject TEXT;
    END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_bookmarks_user_id ON bookmarks(user_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_case_id ON bookmarks(case_id);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);
CREATE INDEX IF NOT EXISTS idx_collections_user_id ON collections(user_id);
CREATE INDEX IF NOT EXISTS idx_collections_public ON collections(is_public) WHERE is_public = TRUE;
