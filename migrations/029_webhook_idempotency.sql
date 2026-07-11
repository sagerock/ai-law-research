-- Ensure a Ko-fi transaction can credit the community pool only once.
WITH duplicate_donations AS (
    SELECT id,
           ROW_NUMBER() OVER (PARTITION BY reference_id ORDER BY id) AS occurrence
    FROM pool_ledger
    WHERE entry_type = 'donation' AND reference_id IS NOT NULL
)
DELETE FROM pool_ledger
WHERE id IN (
    SELECT id FROM duplicate_donations WHERE occurrence > 1
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pool_ledger_unique_donation
    ON pool_ledger (reference_id)
    WHERE entry_type = 'donation' AND reference_id IS NOT NULL;
