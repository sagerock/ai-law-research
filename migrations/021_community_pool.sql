-- Community AI Pool: prepaid balance system
-- Credits from Ko-fi donations and admin top-ups, debits from AI calls

CREATE TABLE IF NOT EXISTS pool_ledger (
    id SERIAL PRIMARY KEY,
    amount DECIMAL(10, 6) NOT NULL,        -- positive = credit, negative = debit
    entry_type TEXT NOT NULL,               -- 'donation', 'admin_credit', 'ai_debit'
    description TEXT,                       -- "Ko-fi from John", "Admin top-up", "study_chat_haiku"
    reference_id TEXT,                      -- kofi_transaction_id or usage context
    created_by TEXT,                        -- 'kofi', admin user_id, or 'system'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pool_ledger_created ON pool_ledger(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_pool_ledger_type ON pool_ledger(entry_type);

-- Ensure site_config exists (may not have been created if migration 003 was skipped)
CREATE TABLE IF NOT EXISTS site_config (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed default config rows if missing
INSERT INTO site_config (key, value, description) VALUES
    ('kofi_username', '', 'Ko-fi donation page username'),
    ('monthly_hosting_cost', '5.00', 'Railway hosting cost per month in USD'),
    ('monthly_goal', '25.00', 'Monthly donation goal in USD')
ON CONFLICT (key) DO NOTHING;

-- Set Ko-fi username so the donate button works
UPDATE site_config SET value = 'sagelewis' WHERE key = 'kofi_username';

-- Add low-balance warning threshold
INSERT INTO site_config (key, value) VALUES ('pool_low_threshold', '5.00')
ON CONFLICT (key) DO NOTHING;
