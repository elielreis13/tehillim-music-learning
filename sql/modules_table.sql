-- Run this in the Supabase SQL editor.
-- Creates the modules table for storing all module content editable via the app.
-- DB rows take priority over .md files for the same slug.

CREATE TABLE IF NOT EXISTS modules (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  number      integer     NOT NULL,
  slug        text        NOT NULL UNIQUE,
  title       text        NOT NULL,
  description text        NOT NULL DEFAULT '',
  topics      text        NOT NULL DEFAULT '',    -- comma-separated
  group_slug  text        NOT NULL DEFAULT '',
  video_url   text        NOT NULL DEFAULT '',
  theory      text        NOT NULL DEFAULT '',
  visual      text        NOT NULL DEFAULT '',
  exercises   jsonb       NOT NULL DEFAULT '[]',  -- [{kind, prompt, options, answer}]
  game        text        NOT NULL DEFAULT '',
  game_kind   text        NOT NULL DEFAULT 'game-challenge',
  created_by  uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS modules_slug_idx   ON modules (slug);
CREATE INDEX IF NOT EXISTS modules_number_idx ON modules (number);

ALTER TABLE modules ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service_all" ON modules USING (true) WITH CHECK (true);

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_modules_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS modules_updated_at ON modules;
CREATE TRIGGER modules_updated_at
  BEFORE UPDATE ON modules
  FOR EACH ROW EXECUTE FUNCTION update_modules_updated_at();
