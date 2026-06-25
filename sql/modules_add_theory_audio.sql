-- Add theory_audio_url column to modules table
ALTER TABLE modules ADD COLUMN IF NOT EXISTS theory_audio_url TEXT NOT NULL DEFAULT '';

-- Create narrations storage bucket (run once in Supabase Dashboard or via this script)
-- NOTE: bucket creation via SQL is not supported — create manually in Storage > New bucket:
--   Name: narrations
--   Public: true (so students can stream without auth)
