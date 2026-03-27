-- Generic legal document builder tables (supports multiple tool types)

-- Legal projects: generic entity for any document builder tool
CREATE TABLE IF NOT EXISTS legal_projects (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    tool_type TEXT NOT NULL,        -- affidavit, memo, complaint, answer, etc.
    title TEXT NOT NULL DEFAULT 'Untitled',
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, generating, complete
    -- Shared case info (plaintiff, defendant, court, jurisdiction, case_number, etc.)
    case_info JSONB DEFAULT '{}',
    -- Tool-specific wizard data (affiant_info, attestable_facts, etc.)
    form_data JSONB DEFAULT '{}',
    -- Generated document
    generated_document TEXT,
    document_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_legal_projects_user ON legal_projects(user_id);
CREATE INDEX IF NOT EXISTS idx_legal_projects_type ON legal_projects(tool_type);

-- Legal documents: uploaded files with extracted text
CREATE TABLE IF NOT EXISTS tool_documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES legal_projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    doc_type TEXT NOT NULL,         -- pleading, evidence, exhibit, affidavit, deposition, discovery
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,                 -- pdf, docx, txt
    extracted_text TEXT,
    char_count INTEGER DEFAULT 0,
    category TEXT,                  -- UI grouping (e.g. 'supporting', 'reference')
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tool_docs_project ON tool_documents(project_id);

-- Legal conversations: chat history for AI refinement
CREATE TABLE IF NOT EXISTS tool_conversations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES legal_projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tool_convos_project ON tool_conversations(project_id);

CREATE TABLE IF NOT EXISTS tool_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES tool_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,              -- user, assistant, system
    content TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tool_messages_convo ON tool_messages(conversation_id);

-- Add tool_type column to existing msj_library for filtering across tool types
ALTER TABLE msj_library ADD COLUMN IF NOT EXISTS tool_type TEXT DEFAULT 'msj';
CREATE INDEX IF NOT EXISTS idx_msj_library_tool_type ON msj_library(tool_type);
