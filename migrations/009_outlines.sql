CREATE TABLE IF NOT EXISTS outlines (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    professor TEXT,
    law_school TEXT,
    semester TEXT,
    description TEXT,
    filename TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,
    is_public BOOLEAN DEFAULT TRUE,
    download_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outlines_user_id ON outlines(user_id);
CREATE INDEX IF NOT EXISTS idx_outlines_subject ON outlines(subject);
CREATE INDEX IF NOT EXISTS idx_outlines_public ON outlines(is_public) WHERE is_public = TRUE;
CREATE INDEX IF NOT EXISTS idx_outlines_created_at ON outlines(created_at DESC);
