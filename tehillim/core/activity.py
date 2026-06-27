"""Audit log: registra o que cada aluno faz e o status de cada ação."""
from __future__ import annotations

import traceback
from contextlib import contextmanager

from flask import request, session

from tehillim.core.supabase import sb_post


def log_activity(
    user_id: str,
    action: str,
    status: str,
    metadata: dict | None = None,
    error_msg: str | None = None,
) -> None:
    """Grava um evento em activity_logs. Nunca levanta exceção."""
    try:
        ip = request.headers.get("X-Forwarded-For", "") or request.remote_addr or ""
        sb_post("activity_logs", {
            "user_id":    user_id,
            "action":     action,
            "status":     status,
            "metadata":   metadata or {},
            "error_msg":  error_msg,
            "ip_address": ip.split(",")[0].strip(),
        })
    except Exception:
        pass


@contextmanager
def activity_scope(user_id: str, action: str, metadata: dict | None = None):
    """
    Grava 'started' ao entrar e 'success'/'error' ao sair.

    Uso:
        with activity_scope(user_id, "upload_recording", {"module_slug": slug}) as ctx:
            # executa a operação
            ctx["audio_url"] = url   # enriquece o log de sucesso
    """
    log_activity(user_id, action, "started", metadata)
    ctx: dict = {}
    try:
        yield ctx
        log_activity(user_id, action, "success", {**(metadata or {}), **ctx})
    except Exception as exc:
        log_activity(
            user_id, action, "error",
            {**(metadata or {}), **ctx},
            error_msg=traceback.format_exc(),
        )
        raise
