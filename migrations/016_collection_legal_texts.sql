CREATE TABLE IF NOT EXISTS collection_legal_texts (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
    legal_text_item_id INTEGER NOT NULL REFERENCES legal_text_items(id) ON DELETE CASCADE,
    notes TEXT,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(collection_id, legal_text_item_id)
);
CREATE INDEX IF NOT EXISTS idx_clt_collection ON collection_legal_texts(collection_id);
CREATE INDEX IF NOT EXISTS idx_clt_legal_text ON collection_legal_texts(legal_text_item_id);
