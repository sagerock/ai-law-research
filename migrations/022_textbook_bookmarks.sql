-- Textbook bookmarks: users can save textbooks for quick access
CREATE TABLE IF NOT EXISTS textbook_bookmarks (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    textbook_id INTEGER NOT NULL REFERENCES casebooks(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, textbook_id)
);

CREATE INDEX IF NOT EXISTS idx_textbook_bookmarks_user_id ON textbook_bookmarks(user_id);
