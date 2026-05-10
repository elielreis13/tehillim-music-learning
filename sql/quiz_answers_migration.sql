-- Garante que a tabela quiz_answers existe com todas as colunas necessárias.
-- Seguro para rodar mesmo se a tabela já existir.

create table if not exists quiz_answers (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  step_index  int  not null default 0,
  step_kind   text not null default '',
  question    text,
  answer      text,
  correct     boolean,
  created_at  timestamptz default now()
);

-- Adiciona colunas caso já exista mas sem elas (idempotente)
alter table quiz_answers add column if not exists step_index int  not null default 0;
alter table quiz_answers add column if not exists step_kind  text not null default '';

alter table quiz_answers enable row level security;

-- Recria a policy sem erro se já existir
do $$ begin
  if not exists (
    select 1 from pg_policies
    where tablename = 'quiz_answers' and policyname = 'own data'
  ) then
    execute 'create policy "own data" on quiz_answers for all using (auth.uid() = user_id)';
  end if;
end $$;
