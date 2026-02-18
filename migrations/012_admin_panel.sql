-- Admin panel: per-user overrides for daily limits and AI models
ALTER TABLE user_tiers ADD COLUMN IF NOT EXISTS daily_limit INTEGER;
ALTER TABLE user_tiers ADD COLUMN IF NOT EXISTS model_override TEXT;

-- Store email on profiles for admin lookup (backfilled from JWT)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS email TEXT;
CREATE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);
