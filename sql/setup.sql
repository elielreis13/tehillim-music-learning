-- ── Progresso dos módulos ─────────────────────────────────────────────────────
create table if not exists module_progress (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  completed   int  not null default 0,
  updated_at  timestamptz default now(),
  unique (user_id, module_slug)
);

-- ── Dias de estudo ────────────────────────────────────────────────────────────
create table if not exists study_days (
  user_id uuid references auth.users(id) on delete cascade,
  day     date not null,
  primary key (user_id, day)
);

-- ── Tentativas de jogos ───────────────────────────────────────────────────────
create table if not exists game_attempts (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text,
  game_kind   text,
  score       numeric,
  created_at  timestamptz default now()
);

-- ── Ativar RLS (Row Level Security) ──────────────────────────────────────────
alter table module_progress enable row level security;
alter table study_days      enable row level security;
alter table game_attempts   enable row level security;

create policy "own data" on module_progress for all using (auth.uid() = user_id);
create policy "own data" on study_days      for all using (auth.uid() = user_id);
create policy "own data" on game_attempts   for all using (auth.uid() = user_id);

-- ── Gravações de áudio ────────────────────────────────────────────────────────
create table if not exists submissions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  audio_path  text not null,
  status      text not null default 'pending',
  created_at  timestamptz default now()
);

alter table submissions enable row level security;
create policy "own data" on submissions for all using (auth.uid() = user_id);

-- ── Controle de acesso (professor libera módulos para alunos) ─────────────────
create table if not exists student_access (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  granted_at  timestamptz default now(),
  unique (user_id, module_slug)
);

alter table student_access enable row level security;
create policy "read own access" on student_access
  for select to authenticated
  using (auth.uid() = user_id);

-- ── Respostas de quiz ─────────────────────────────────────────────────────────
create table if not exists quiz_answers (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  step_index  int  not null,
  step_kind   text not null,
  question    text,
  answer      text,
  correct     boolean,
  created_at  timestamptz default now()
);

alter table quiz_answers enable row level security;
create policy "own data" on quiz_answers for all using (auth.uid() = user_id);

-- ── Comentários do professor ──────────────────────────────────────────────────
create table if not exists teacher_comments (
  id          uuid primary key default gen_random_uuid(),
  student_id  uuid references auth.users(id) on delete cascade,
  module_slug text,
  content     text not null,
  created_at  timestamptz default now()
);

alter table teacher_comments enable row level security;
create policy "read own comments" on teacher_comments
  for select to authenticated
  using (auth.uid() = student_id);

-- ── Políticas de armazenamento de áudio ──────────────────────────────────────
-- (requer que o bucket 'recordings' já exista no Storage do Supabase)

create policy "upload own recordings" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'recordings'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

create policy "read own recordings" on storage.objects
  for select to authenticated
  using (
    bucket_id = 'recordings'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
