-- ── Mensagens professor ↔ aluno ───────────────────────────────────────────────
create table if not exists messages (
  id          uuid primary key default gen_random_uuid(),
  student_id  uuid not null references auth.users(id) on delete cascade,
  sender_type text not null check (sender_type in ('teacher', 'student')),
  module_slug text,
  content     text not null,
  read_at     timestamptz,
  created_at  timestamptz default now()
);

alter table messages enable row level security;

-- Aluno lê as próprias mensagens
create policy "read own messages" on messages
  for select to authenticated
  using (auth.uid() = student_id);

-- Aluno envia mensagem como 'student'
create policy "student send message" on messages
  for insert to authenticated
  with check (auth.uid() = student_id and sender_type = 'student');

-- Aluno marca as próprias mensagens como lidas
create policy "student mark read" on messages
  for update to authenticated
  using (auth.uid() = student_id)
  with check (auth.uid() = student_id);
