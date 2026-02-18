-- Study notes (uploaded files + extracted text)
CREATE TABLE IF NOT EXISTS study_notes (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL,
    subject TEXT,
    filename TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,
    extracted_text TEXT,
    char_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_study_notes_user_id ON study_notes(user_id);

-- Chat conversations
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    note_ids INTEGER[],
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Chat messages
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);

-- User tier & daily usage
CREATE TABLE IF NOT EXISTS user_tiers (
    user_id TEXT PRIMARY KEY,
    tier TEXT NOT NULL DEFAULT 'free',
    messages_today INTEGER DEFAULT 0,
    last_message_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
