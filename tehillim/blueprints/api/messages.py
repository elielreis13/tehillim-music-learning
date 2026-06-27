from __future__ import annotations

from flask import abort, current_app, jsonify, request, session
import requests as http

from . import bp
from tehillim.extensions import (
    sb_get, sb_headers, sb_post,
    require_teacher_token, log_activity,
)
from .progress import _now_iso


# ── API Aluno — mensagens ──────────────────────────────────────────────────────

@bp.get("/messages")
def student_messages():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        rows = sb_get("messages", {
            "select":     "id,sender_type,module_slug,step_index,question_preview,content,read_at,created_at",
            "student_id": f"eq.{user_id}",
            "order":      "created_at.asc",
        })
        return jsonify({"messages": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.post("/messages")
def student_send_message():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    body        = request.get_json(silent=True) or {}
    content     = body.get("content", "").strip()
    module_slug = body.get("module_slug") or None
    if not content:
        abort(400)
    row = sb_post("messages", {
        "student_id": user_id, "sender_type": "student",
        "content": content, "module_slug": module_slug,
    })
    log_activity(user_id, "send_message", "success", {"module_slug": module_slug})
    return jsonify(row[0] if isinstance(row, list) else row), 201


@bp.patch("/messages/<msg_id>/read")
def student_mark_message_read(msg_id: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    supabase_url = current_app.config["SUPABASE_URL"]
    http.patch(
        f"{supabase_url}/rest/v1/messages",
        headers={**sb_headers(), "Prefer": "return=minimal"},
        params={"id": f"eq.{msg_id}", "student_id": f"eq.{user_id}"},
        json={"read_at": _now_iso()},
        timeout=10,
    )
    return "", 204


@bp.get("/messages/unread-count")
def student_unread_count():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"count": 0})
    try:
        rows = sb_get("messages", {"select": "id", "student_id": f"eq.{user_id}",
                                   "sender_type": "eq.teacher", "read_at": "is.null"})
        return jsonify({"count": len(rows)})
    except Exception:
        return jsonify({"count": 0})


# ── API Professor — mensagens ──────────────────────────────────────────────────

@bp.post("/teacher/comments")
def teacher_add_comment():
    if err := require_teacher_token():
        return err
    body        = request.get_json(silent=True) or {}
    student_id  = body.get("student_id", "").strip()
    content     = body.get("content", "").strip()
    module_slug = body.get("module_slug") or None
    if not student_id or not content:
        abort(400)
    result = sb_post("teacher_comments", {"student_id": student_id, "content": content, "module_slug": module_slug})
    return jsonify(result[0]), 201


@bp.delete("/teacher/comments/<comment_id>")
def teacher_delete_comment(comment_id: str):
    if err := require_teacher_token():
        return err
    from tehillim.extensions import sb_delete
    sb_delete("teacher_comments", {"id": f"eq.{comment_id}"})
    return "", 204


@bp.post("/teacher/student/<user_id>/messages")
def teacher_send_message(user_id: str):
    if err := require_teacher_token():
        return err
    body             = request.get_json(silent=True) or {}
    content          = body.get("content", "").strip()
    module_slug      = body.get("module_slug") or None
    step_index       = body.get("step_index")
    question_preview = (body.get("question_preview") or "").strip() or None
    if not content:
        abort(400)
    payload = {
        "student_id": user_id, "sender_type": "teacher",
        "content": content, "module_slug": module_slug,
    }
    if step_index is not None:
        payload["step_index"] = int(step_index)
    if question_preview:
        payload["question_preview"] = question_preview[:200]
    row = sb_post("messages", payload)
    return jsonify(row[0] if isinstance(row, list) else row), 201


@bp.get("/teacher/student/<user_id>/messages")
def teacher_student_messages(user_id: str):
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("messages", {
            "select":     "id,sender_type,module_slug,step_index,question_preview,content,read_at,created_at",
            "student_id": f"eq.{user_id}",
            "order":      "created_at.asc",
        })
        return jsonify({"messages": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.patch("/teacher/student/<user_id>/messages/read-all")
def teacher_mark_all_student_messages_read(user_id: str):
    """Marca como lidas todas as mensagens do aluno ainda não lidas (sender_type=student)."""
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    http.patch(
        f"{supabase_url}/rest/v1/messages",
        headers={**sb_headers(), "Prefer": "return=minimal"},
        params={"student_id": f"eq.{user_id}", "sender_type": "eq.student", "read_at": "is.null"},
        json={"read_at": _now_iso()},
        timeout=10,
    )
    return "", 204


@bp.patch("/teacher/messages/<msg_id>/read")
def teacher_mark_message_read(msg_id: str):
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    http.patch(
        f"{supabase_url}/rest/v1/messages",
        headers={**sb_headers(), "Prefer": "return=minimal"},
        params={"id": f"eq.{msg_id}"},
        json={"read_at": _now_iso()},
        timeout=10,
    )
    return "", 204


@bp.post("/teacher/student/<user_id>/audio-message")
def teacher_send_audio_message(user_id: str):
    """Professor envia mensagem de áudio para o aluno. Salva no Storage e registra como mensagem."""
    if err := require_teacher_token():
        return err
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    import uuid as _uuid
    from flask import current_app
    ext = "webm" if "webm" in (f.content_type or "") else "ogg"
    filename = f"teacher-replies/{user_id}/{_uuid.uuid4().hex}.{ext}"
    sb_url  = current_app.config["SUPABASE_URL"]
    svc_key = current_app.config["SUPABASE_SERVICE_KEY"]

    r = http.post(
        f"{sb_url}/storage/v1/object/recordings/{filename}",
        headers={"apikey": svc_key, "Authorization": f"Bearer {svc_key}",
                 "Content-Type": f.content_type or "audio/webm", "x-upsert": "true"},
        data=f.read(), timeout=30,
    )
    if not r.ok:
        return jsonify({"error": f"Storage: {r.status_code}"}), 500

    audio_url   = f"{sb_url}/storage/v1/object/public/recordings/{filename}"
    module_slug = request.form.get("module_slug") or None
    label       = request.form.get("label") or ""
    prefix      = f"[🎤 {label}]\n" if label else ""
    row = sb_post("messages", {
        "student_id":  user_id,
        "sender_type": "teacher",
        "module_slug": module_slug,
        "content":     f"{prefix}🎤 [Áudio do professor]({audio_url})",
    })
    return jsonify(row[0] if isinstance(row, list) else row), 201


@bp.get("/teacher/messages/unread")
def teacher_unread_messages():
    """Retorna contagem de msgs não lidas de alunos, agrupada por aluno."""
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("messages", {
            "select":      "student_id",
            "sender_type": "eq.student",
            "read_at":     "is.null",
        })
    except Exception as exc:
        return jsonify({"total": 0, "students": [], "error": str(exc)})

    from collections import Counter
    counts = Counter(r["student_id"] for r in rows)
    return jsonify({
        "total":    sum(counts.values()),
        "students": [{"id": sid, "count": c} for sid, c in counts.items()],
    })
