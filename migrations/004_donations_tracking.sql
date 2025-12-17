-- Donations tracking for Ko-fi webhook integration
-- Migration 004: Track individual donations automatically

CREATE TABLE IF NOT EXISTS donations (
    id SERIAL PRIMARY KEY,
    kofi_transaction_id VARCHAR(100) UNIQUE,  -- Prevent duplicate processing
    from_name VARCHAR(255),
    message TEXT,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'USD',
    donation_type VARCHAR(50),  -- 'Donation', 'Subscription', etc.
    is_public BOOLEAN DEFAULT true,
    is_subscription BOOLEAN DEFAULT false,
    tier_name VARCHAR(100),
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    raw_data JSONB  -- Store full webhook payload for reference
);

-- Index for monthly aggregation queries
CREATE INDEX IF NOT EXISTS idx_donations_received_at ON donations(received_at DESC);
CREATE INDEX IF NOT EXISTS idx_donations_month ON donations(DATE_TRUNC('month', received_at));
