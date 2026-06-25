  -- ── Migration: adicionar contexto de atividade às mensagens ───────────────────
  -- Execute este arquivo após messages.sql

  alter table messages
    add column if not exists step_index       integer,
    add column if not exists question_preview text;

  -- Índice para busca rápida de mensagens não lidas por aluno
  create index if not exists messages_student_unread
    on messages (student_id, sender_type, read_at)
    where read_at is null;
