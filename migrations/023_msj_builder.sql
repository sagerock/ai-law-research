-- Motion for Summary Judgment builder tables

-- MSJ projects: main entity storing wizard form data
CREATE TABLE IF NOT EXISTS msj_projects (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT 'Untitled Motion',
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, generating, complete
    -- Step 1: Case info
    case_info JSONB DEFAULT '{}',
    -- Step 3: Statement of undisputed material facts
    material_facts JSONB DEFAULT '[]',
    -- Step 5: Legal arguments
    legal_arguments JSONB DEFAULT '[]',
    -- Generated motion
    generated_motion TEXT,
    motion_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_msj_projects_user ON msj_projects(user_id);

-- MSJ documents: uploaded files with extracted text
CREATE TABLE IF NOT EXISTS msj_documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES msj_projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    doc_type TEXT NOT NULL,       -- pleading, evidence, exhibit, affidavit, deposition
    title TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_size INTEGER,
    file_type TEXT,               -- pdf, docx, txt
    extracted_text TEXT,
    char_count INTEGER DEFAULT 0,
    step INTEGER NOT NULL,        -- 2 (pleadings) or 4 (evidence)
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_msj_docs_project ON msj_documents(project_id);

-- MSJ conversations: chat history for AI refinement (Step 6)
CREATE TABLE IF NOT EXISTS msj_conversations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES msj_projects(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_msj_convos_project ON msj_conversations(project_id);

CREATE TABLE IF NOT EXISTS msj_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES msj_conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,            -- user, assistant, system
    content TEXT NOT NULL,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_msj_messages_convo ON msj_messages(conversation_id);

-- MSJ library: admin-curated approved templates and standards
CREATE TABLE IF NOT EXISTS msj_library (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    doc_type TEXT NOT NULL,       -- template, standard, sample_motion, local_rule
    jurisdiction TEXT,            -- federal, california, etc.
    court TEXT,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_msj_library_type ON msj_library(doc_type);
CREATE INDEX IF NOT EXISTS idx_msj_library_jurisdiction ON msj_library(jurisdiction);
