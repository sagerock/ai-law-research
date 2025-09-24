-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Courts table
CREATE TABLE IF NOT EXISTS courts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    jurisdiction TEXT,
    level TEXT, -- federal, state, appellate, trial
    abbreviation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Main cases table
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
    embedding vector(1536), -- For semantic search
    metadata JSONB,
    source_url TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Case chunks for granular search
CREATE TABLE IF NOT EXISTS case_chunks (
    id SERIAL PRIMARY KEY,
    case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    chunk_index INTEGER,
    section TEXT, -- syllabus, majority, dissent, etc.
    content TEXT,
    embedding vector(1536),
    tokens INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Citations between cases
CREATE TABLE IF NOT EXISTS citations (
    id SERIAL PRIMARY KEY,
    source_case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    target_case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    context_span TEXT,
    signal TEXT, -- followed, distinguished, overruled, etc.
    paragraph_num INTEGER,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_case_id, target_case_id, paragraph_num)
);

-- Treatment tracking for citator
CREATE TABLE IF NOT EXISTS treatments (
    id SERIAL PRIMARY KEY,
    case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    treatment_type TEXT, -- positive, negative, neutral
    signal TEXT,
    citing_case_id TEXT REFERENCES cases(id),
    snippet TEXT,
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User collections for saved cases
CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Cases in collections
CREATE TABLE IF NOT EXISTS collection_cases (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
    case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    notes TEXT,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(collection_id, case_id)
);

-- Brief check uploads
CREATE TABLE IF NOT EXISTS brief_checks (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT,
    content TEXT,
    citations_found JSONB,
    missing_authorities JSONB,
    negative_treatments JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ETL job tracking
CREATE TABLE IF NOT EXISTS etl_jobs (
    id SERIAL PRIMARY KEY,
    job_type TEXT,
    status TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    records_processed INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    metadata JSONB
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_cases_date ON cases(decision_date DESC);
CREATE INDEX IF NOT EXISTS idx_cases_court ON cases(court_id);
CREATE INDEX IF NOT EXISTS idx_cases_reporter ON cases(reporter_cite);
CREATE INDEX IF NOT EXISTS idx_citations_source ON citations(source_case_id);
CREATE INDEX IF NOT EXISTS idx_citations_target ON citations(target_case_id);
CREATE INDEX IF NOT EXISTS idx_treatments_case ON treatments(case_id);

-- Vector similarity indexes (using IVFFlat for performance)
CREATE INDEX IF NOT EXISTS idx_cases_embedding
    ON cases USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON case_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_cases_content_fts
    ON cases USING gin(to_tsvector('english', content));

CREATE INDEX IF NOT EXISTS idx_chunks_content_fts
    ON case_chunks USING gin(to_tsvector('english', content));

-- Insert some initial courts
INSERT INTO courts (name, jurisdiction, level, abbreviation) VALUES
    ('United States Supreme Court', 'federal', 'supreme', 'SCOTUS'),
    ('U.S. Court of Appeals for the Ninth Circuit', 'federal', 'appellate', 'CA9'),
    ('U.S. Court of Appeals for the Second Circuit', 'federal', 'appellate', 'CA2'),
    ('U.S. Court of Appeals for the Federal Circuit', 'federal', 'appellate', 'CAFC'),
    ('U.S. District Court for the Southern District of New York', 'federal', 'trial', 'SDNY'),
    ('U.S. District Court for the Northern District of California', 'federal', 'trial', 'NDCA')
ON CONFLICT (name) DO NOTHING;

-- Helper function for similarity search
CREATE OR REPLACE FUNCTION search_similar_cases(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    case_id TEXT,
    title TEXT,
    court_id INT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id as case_id,
        c.title,
        c.court_id,
        1 - (c.embedding <=> query_embedding) as similarity
    FROM cases c
    WHERE c.embedding IS NOT NULL
    AND 1 - (c.embedding <=> query_embedding) > match_threshold
    ORDER BY c.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Function to calculate citator badge
CREATE OR REPLACE FUNCTION calculate_citator_badge(target_case_id TEXT)
RETURNS TEXT
LANGUAGE plpgsql
AS $$
DECLARE
    negative_count INT;
    overruled_count INT;
BEGIN
    SELECT COUNT(*) INTO overruled_count
    FROM citations
    WHERE target_case_id = target_case_id
    AND signal IN ('overruled', 'abrogated');

    IF overruled_count > 0 THEN
        RETURN 'red';
    END IF;

    SELECT COUNT(*) INTO negative_count
    FROM citations
    WHERE target_case_id = target_case_id
    AND signal IN ('criticized', 'questioned', 'distinguished');

    IF negative_count > 0 THEN
        RETURN 'yellow';
    END IF;

    RETURN 'green';
END;
$$;