-- Tabela para gravações de prática dos alunos (Método Bona)
-- Execute no Supabase SQL Editor

CREATE TABLE IF NOT EXISTS submissions (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  module_slug  TEXT NOT NULL,
  audio_url    TEXT NOT NULL,
  professor_note TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS submissions_module_slug_idx ON submissions (module_slug);
CREATE INDEX IF NOT EXISTS submissions_user_id_idx     ON submissions (user_id);

-- RLS: aluno só vê as próprias; professor vê todas
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "aluno lê próprias gravações"
  ON submissions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "service role acesso total"
  ON submissions FOR ALL
  USING (true)
  WITH CHECK (true);
