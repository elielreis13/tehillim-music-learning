CREATE TABLE IF NOT EXISTS activity_logs (
    id          UUID        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     UUID        NOT NULL,
    action      TEXT        NOT NULL,
    status      TEXT        NOT NULL CHECK (status IN ('started', 'success', 'error')),
    metadata    JSONB       DEFAULT '{}'::jsonb,
    error_msg   TEXT,
    ip_address  TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_user_action
    ON activity_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_activity_logs_action_time
    ON activity_logs (action, created_at DESC);

-- Facilita buscar todas as ações que falharam
CREATE INDEX IF NOT EXISTS idx_activity_logs_errors
    ON activity_logs (created_at DESC)
    WHERE status = 'error';

ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;
-- Sem policies públicas: apenas service role (backend) tem acesso
