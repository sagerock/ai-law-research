-- 018_study_sessions.sql
-- ADHD Law Study Session Engine: mindmaps, nodes, sessions, and progress tracking

CREATE TABLE IF NOT EXISTS mindmaps (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    tree JSONB NOT NULL,
    node_count INTEGER DEFAULT 0,
    max_depth INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_mindmaps_user ON mindmaps(user_id);

CREATE TABLE IF NOT EXISTS mindmap_nodes (
    id SERIAL PRIMARY KEY,
    mindmap_id INTEGER NOT NULL REFERENCES mindmaps(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,
    parent_node_id TEXT,
    depth INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL,
    is_leaf BOOLEAN DEFAULT false,
    case_refs JSONB DEFAULT '[]',
    rule_refs JSONB DEFAULT '[]',
    sort_order INTEGER DEFAULT 0,
    UNIQUE(mindmap_id, node_id)
);
CREATE INDEX IF NOT EXISTS idx_mnodes_mindmap ON mindmap_nodes(mindmap_id);

CREATE TABLE IF NOT EXISTS study_sessions (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    mindmap_id INTEGER NOT NULL REFERENCES mindmaps(id) ON DELETE CASCADE,
    current_node_id TEXT,
    current_question TEXT,
    phase TEXT DEFAULT 'quiz',
    session_state TEXT DEFAULT 'active',
    mode TEXT DEFAULT 'quiz',
    streak INTEGER DEFAULT 0,
    max_streak INTEGER DEFAULT 0,
    nodes_visited INTEGER DEFAULT 0,
    nodes_mastered INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    total_incorrect INTEGER DEFAULT 0,
    branch_node_id TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    last_activity_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON study_sessions(user_id);

CREATE TABLE IF NOT EXISTS node_progress (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    mindmap_id INTEGER NOT NULL REFERENCES mindmaps(id) ON DELETE CASCADE,
    node_id TEXT NOT NULL,
    correct_streak INTEGER DEFAULT 0,
    total_attempts INTEGER DEFAULT 0,
    total_correct INTEGER DEFAULT 0,
    mastery TEXT DEFAULT 'unseen',
    last_response_time_ms INTEGER,
    last_response_length INTEGER,
    last_reviewed_at TIMESTAMP,
    UNIQUE(user_id, mindmap_id, node_id)
);
CREATE INDEX IF NOT EXISTS idx_nprog_user_map ON node_progress(user_id, mindmap_id);
