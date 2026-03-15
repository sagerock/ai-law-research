-- BYOK (Bring Your Own Key) support
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS encrypted_api_key TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS api_key_preview TEXT;  -- "sk-ant-...xxxx"

-- Add source column to api_usage_log to differentiate BYOK vs site-funded usage
ALTER TABLE api_usage_log ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'site';
