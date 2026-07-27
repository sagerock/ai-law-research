-- Durable, restart-safe lifecycle markers for AI pool reservations.

CREATE UNIQUE INDEX IF NOT EXISTS idx_pool_ledger_ai_reservation
    ON pool_ledger (reference_id)
    WHERE entry_type = 'ai_reservation' AND reference_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_pool_ledger_ai_reservation_finalized
    ON pool_ledger (reference_id)
    WHERE entry_type = 'ai_reservation_finalized' AND reference_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_pool_ledger_ai_reservation_uncertain
    ON pool_ledger (reference_id)
    WHERE entry_type = 'ai_reservation_uncertain' AND reference_id IS NOT NULL;
