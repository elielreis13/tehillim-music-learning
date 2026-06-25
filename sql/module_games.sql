-- Tabela de jogos criados pelo professor para enriquecer módulos existentes.
-- Execute no Supabase SQL Editor antes de usar a página /admin/jogos.

CREATE TABLE IF NOT EXISTS module_games (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  module_slug text        NOT NULL,
  title       text        NOT NULL,
  description text        NOT NULL DEFAULT '',
  game_kind   text        NOT NULL,
  body        text        NOT NULL DEFAULT '',
  game_data   jsonb       NOT NULL DEFAULT '{}'::jsonb,
  order_index integer     NOT NULL DEFAULT 0,
  created_by  uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS module_games_slug_idx ON module_games (module_slug, order_index);

ALTER TABLE module_games ENABLE ROW LEVEL SECURITY;

-- Service role tem acesso total (usado pelo backend Flask)
CREATE POLICY "service_all" ON module_games
  USING (true)
  WITH CHECK (true);
