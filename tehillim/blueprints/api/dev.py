"""Endpoints de diagnóstico — acesso exclusivo do owner."""
from __future__ import annotations

from flask import jsonify, request

from . import bp
from tehillim.extensions import require_owner_token, sb_get, sb_patch


@bp.get("/dev/activity-log/<user_id>")
def dev_activity_log(user_id: str):
    """
    Retorna o histórico de ações de um aluno.

    Query params opcionais:
      action  — filtra por tipo de ação (ex: upload_recording)
      status  — filtra por status (started | success | error)
      limit   — máximo de registros (padrão 100, max 500)
    """
    if err := require_owner_token():
        return err

    action = request.args.get("action")
    status = request.args.get("status")
    limit  = min(int(request.args.get("limit", 100)), 500)

    params: dict = {
        "select":   "id,action,status,metadata,error_msg,ip_address,created_at",
        "user_id":  f"eq.{user_id}",
        "order":    "created_at.desc",
        "limit":    str(limit),
    }
    if action:
        params["action"] = f"eq.{action}"
    if status:
        params["status"] = f"eq.{status}"

    try:
        rows = sb_get("activity_logs", params)
        return jsonify({"user_id": user_id, "count": len(rows), "logs": rows}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/dev/activity-log/errors")
def dev_activity_errors():
    """
    Lista as últimas ações com status=error de todos os alunos.

    Query params opcionais:
      action  — filtra por tipo de ação
      limit   — máximo de registros (padrão 50, max 200)
    """
    if err := require_owner_token():
        return err

    action = request.args.get("action")
    limit  = min(int(request.args.get("limit", 50)), 200)

    params: dict = {
        "select": "id,user_id,action,metadata,error_msg,ip_address,created_at",
        "status": "eq.error",
        "order":  "created_at.desc",
        "limit":  str(limit),
    }
    if action:
        params["action"] = f"eq.{action}"

    try:
        rows = sb_get("activity_logs", params)
        return jsonify({"count": len(rows), "errors": rows}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/dev/activity-log/orphans")
def dev_activity_orphans():
    """
    Detecta ações que ficaram como 'started' sem 'success' ou 'error' posterior.
    Indica requests que travaram ou crasharam no meio.

    Query params opcionais:
      action   — filtra por tipo de ação
      minutes  — janela de tempo em minutos (padrão 60, max 1440)
    """
    if err := require_owner_token():
        return err

    action  = request.args.get("action")
    minutes = min(int(request.args.get("minutes", 60)), 1440)

    # Busca 'started' recentes
    params_started: dict = {
        "select":     "id,user_id,action,metadata,ip_address,created_at",
        "status":     "eq.started",
        "created_at": f"gte.now()-interval'{minutes} minutes'",
        "order":      "created_at.desc",
        "limit":      "200",
    }
    if action:
        params_started["action"] = f"eq.{action}"

    # Busca 'success' e 'error' no mesmo período para cruzar
    params_done: dict = {
        "select":     "user_id,action,created_at",
        "status":     "in.(success,error)",
        "created_at": f"gte.now()-interval'{minutes} minutes'",
        "limit":      "1000",
    }

    try:
        started = sb_get("activity_logs", params_started)
        done    = sb_get("activity_logs", params_done)

        # Um 'started' é órfão se não existe um 'success'/'error' com
        # mesmo user_id + action E created_at posterior
        done_keys = {
            (r["user_id"], r["action"]): r["created_at"]
            for r in done
        }

        orphans = [
            r for r in started
            if (r["user_id"], r["action"]) not in done_keys
            or done_keys[(r["user_id"], r["action"])] < r["created_at"]
        ]

        return jsonify({"minutes": minutes, "count": len(orphans), "orphans": orphans}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
