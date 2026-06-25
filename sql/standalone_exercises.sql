-- Standalone exercises created by the professor (one-off, not tied to modules)

CREATE TABLE IF NOT EXISTS standalone_exercises (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id  uuid NOT NULL,
  title       text NOT NULL,
  prompt      text NOT NULL DEFAULT '',
  game_kind   text NOT NULL,          -- e.g. "game-quiz", "game-challenge"
  game_data   jsonb NOT NULL DEFAULT '{}',
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Who receives each exercise (null student_id = all students of that teacher)
CREATE TABLE IF NOT EXISTS standalone_assignments (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  exercise_id uuid NOT NULL REFERENCES standalone_exercises(id) ON DELETE CASCADE,
  student_id  uuid,                   -- null = all students
  created_at  timestamptz NOT NULL DEFAULT now()
);

-- Track which students have completed each exercise
CREATE TABLE IF NOT EXISTS standalone_completions (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  exercise_id uuid NOT NULL REFERENCES standalone_exercises(id) ON DELETE CASCADE,
  student_id  uuid NOT NULL,
  completed_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (exercise_id, student_id)
);

-- RLS: teachers manage their own exercises
ALTER TABLE standalone_exercises    ENABLE ROW LEVEL SECURITY;
ALTER TABLE standalone_assignments  ENABLE ROW LEVEL SECURITY;
ALTER TABLE standalone_completions  ENABLE ROW LEVEL SECURITY;

-- Service-role bypass (backend uses service key)
CREATE POLICY "service_all" ON standalone_exercises    FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_all" ON standalone_assignments  FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "service_all" ON standalone_completions  FOR ALL USING (true) WITH CHECK (true);

-- ── Migration: if you already have the old schema (kind/options/answer), run: ──
-- ALTER TABLE standalone_exercises
--   ADD COLUMN IF NOT EXISTS game_kind text,
--   ADD COLUMN IF NOT EXISTS game_data jsonb DEFAULT '{}',
--   DROP COLUMN IF EXISTS kind,
--   DROP COLUMN IF EXISTS options,
--   DROP COLUMN IF EXISTS answer;
-- UPDATE standalone_exercises SET game_kind = 'game-quiz' WHERE game_kind IS NULL;
-- ALTER TABLE standalone_exercises ALTER COLUMN game_kind SET NOT NULL;
