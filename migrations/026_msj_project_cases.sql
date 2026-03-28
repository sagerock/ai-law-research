-- Per-project approved case sources for MSJ builder
CREATE TABLE IF NOT EXISTS msj_project_cases (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES msj_projects(id) ON DELETE CASCADE,
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    added_by TEXT NOT NULL,
    notes TEXT,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, case_id)
);

CREATE INDEX idx_msj_project_cases_project ON msj_project_cases(project_id);
