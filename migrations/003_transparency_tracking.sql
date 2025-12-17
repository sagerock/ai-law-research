-- Transparency dashboard tracking tables
-- Migration 003: Track API usage and site configuration

-- Track API usage by day (for live cost tracking)
CREATE TABLE IF NOT EXISTS api_usage_log (
    id SERIAL PRIMARY KEY,
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    usage_type VARCHAR(50) NOT NULL,  -- 'ai_summary', 'embedding', etc.
    call_count INTEGER DEFAULT 0,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(usage_date, usage_type)
);

-- Site configuration for transparency values (editable without code changes)
CREATE TABLE IF NOT EXISTS site_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default configuration values
INSERT INTO site_config (key, value, description) VALUES
    ('monthly_hosting_cost', '5.00', 'Railway hosting cost per month in USD'),
    ('monthly_goal', '25.00', 'Monthly donation goal in USD'),
    ('monthly_donations', '0.00', 'Donations received this month (manually updated)'),
    ('kofi_username', '', 'Ko-fi donation page username'),
    ('charity_name', 'Houseless Movement', 'Name of charity receiving surplus'),
    ('charity_description', 'Supporting unhoused individuals in our community', 'Description of charity mission'),
    ('charity_url', '', 'Link to charity website')
ON CONFLICT (key) DO NOTHING;

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_usage_date ON api_usage_log(usage_date DESC);
CREATE INDEX IF NOT EXISTS idx_api_usage_type ON api_usage_log(usage_type);
