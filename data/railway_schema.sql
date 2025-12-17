-- Schema for Railway PostgreSQL (without pgvector)

-- Courts table
CREATE TABLE IF NOT EXISTS courts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    jurisdiction TEXT,
    level TEXT,
    abbreviation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Main cases table (no embedding column)
CREATE TABLE IF NOT EXISTS cases (
    id TEXT PRIMARY KEY,
    court_id INTEGER REFERENCES courts(id),
    title TEXT NOT NULL,
    docket_number TEXT,
    decision_date DATE,
    reporter_cite TEXT,
    neutral_cite TEXT,
    precedential BOOLEAN DEFAULT TRUE,
    content TEXT,
    content_hash TEXT,
    metadata JSONB,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Citations between cases
CREATE TABLE IF NOT EXISTS citations (
    id SERIAL PRIMARY KEY,
    source_case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    target_case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    context_span TEXT,
    signal TEXT,
    paragraph_num INTEGER,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_case_id, target_case_id, paragraph_num)
);

-- AI summaries cache
CREATE TABLE IF NOT EXISTS ai_summaries (
    id SERIAL PRIMARY KEY,
    case_id TEXT REFERENCES cases(id) ON DELETE CASCADE UNIQUE,
    summary TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10, 6),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_cases_title ON cases(title);
CREATE INDEX IF NOT EXISTS idx_cases_decision_date ON cases(decision_date);
CREATE INDEX IF NOT EXISTS idx_cases_court_id ON cases(court_id);
CREATE INDEX IF NOT EXISTS idx_citations_source ON citations(source_case_id);
CREATE INDEX IF NOT EXISTS idx_citations_target ON citations(target_case_id);
