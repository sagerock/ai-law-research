-- Add author_name column to store display name at time of posting
-- This avoids relying on profiles table lookup

ALTER TABLE comments ADD COLUMN IF NOT EXISTS author_name TEXT;
