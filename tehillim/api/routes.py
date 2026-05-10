from __future__ import annotations

from flask import abort, current_app, jsonify, request, session
import requests as http

from . import bp
from tehillim.content import (
    get_module, groups_summary, modules_payload,
    get_student_extra_lessons, add_student_extra_lesson, delete_student_extra_lesson,
)
from tehillim.content.demo_games import DEMO_GAMES
from tehillim.extensions import (
    sb_delete, sb_get, sb_headers, sb_post, sb_put,
    require_teacher_token,
)


# ── Jogos ─────────────────────────────────────────────────────────────────────

@bp.get("/games/demo")
def games_demo():
    return jsonify({"games": DEMO_GAMES})


# ── Conteúdo público ──────────────────────────────────────────────────────────

@bp.get("/groups")
def group_list():
    return jsonify({"groups": groups_summary()})


@bp.get("/modules")
def modules():
    return jsonify({"modules": modules_payload()})


@bp.get("/modules/<module_slug>")
def module_content(module_slug: str):
    selected_module = get_module(module_slug)
    if selected_module is None:
        abort(404)
    return jsonify(selected_module.to_payload())


@bp.get("/bona/<slug>")
def bona_sheet(slug: str):
    from pathlib import Path
    from flask import send_file
    sheet_path = Path(__file__).resolve().parent.parent / "static" / "bona" / f"{slug}.musicxml"
    if not sheet_path.exists():
        abort(404)
    return send_file(sheet_path, mimetype="application/xml")


# ── Acesso do aluno ───────────────────────────────────────────────────────────

@bp.get("/my-access")
def my_access():
    if not session.get("user_id"):
        return jsonify({"slugs": [], "isTeacher": False})
    if session.get("is_teacher"):
        return jsonify({"slugs": [], "isTeacher": True})
    try:
        rows  = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{session['user_id']}"})
        slugs = [r["module_slug"] for r in rows]
        session["module_slugs"] = slugs
        return jsonify({"slugs": slugs, "isTeacher": False})
    except Exception:
        return jsonify({"slugs": session.get("module_slugs", []), "isTeacher": False})


# ── Progresso ─────────────────────────────────────────────────────────────────

@bp.post("/quiz-answer")
def save_quiz_answer():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    body = request.get_json(silent=True) or {}
    module_slug = body.get("module_slug", "").strip()
    step_index  = body.get("step_index")
    step_kind   = body.get("step_kind", "").strip()
    question    = body.get("question") or None
    answer      = body.get("answer") or None
    correct     = body.get("correct")
    if not module_slug or step_index is None:
        abort(400)
    try:
        sb_post("quiz_answers", {
            "user_id":     user_id,
            "module_slug": module_slug,
            "step_index":  int(step_index),
            "step_kind":   step_kind,
            "question":    question,
            "answer":      answer,
            "correct":     bool(correct),
        }, prefer="return=minimal")
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.post("/progress")
def save_progress():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    body        = request.get_json(silent=True) or {}
    module_slug = body.get("module_slug", "").strip()
    completed   = int(body.get("completed", 0))
    if not module_slug:
        abort(400)
    try:
        sb_post("module_progress", {
            "user_id": user_id, "module_slug": module_slug,
            "completed": completed, "updated_at": _now_iso(),
        })
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.get("/study-days")
def get_study_days():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"days": []}), 401
    try:
        rows = sb_get("study_days", {"select": "day", "user_id": f"eq.{user_id}", "order": "day.desc"})
        return jsonify({"days": [r["day"] for r in rows]})
    except Exception:
        return jsonify({"days": []})


@bp.post("/study-day")
def mark_study_day():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    day = _today()
    try:
        sb_post("study_days", {"user_id": user_id, "day": day})
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.post("/me/name")
def update_name():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    name = (request.get_json(silent=True) or {}).get("name", "").strip()
    if not name:
        abort(400)
    session["name"] = name
    # Atualiza metadado no Supabase em background (best-effort)
    try:
        sb_put(f"/auth/v1/admin/users/{user_id}", {"user_metadata": {"name": name}})
    except Exception:
        pass
    return jsonify({"ok": True, "name": name})


# ── API Professor ─────────────────────────────────────────────────────────────

@bp.get("/teacher/students")
def teacher_students():
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        params={"per_page": 200},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"users": []})

    from collections import defaultdict
    users_raw = r.json().get("users", [])
    users = {
        u["id"]: {
            "email": u["email"],
            "name":  (u.get("user_metadata") or {}).get("name") or "",
            "role":  (u.get("user_metadata") or {}).get("role") or "",
        }
        for u in users_raw
    }

    try:
        progress = sb_get("module_progress", {"select": "user_id,module_slug,completed,updated_at", "order": "updated_at.desc"})
        study    = sb_get("study_days",      {"select": "user_id,day", "order": "day.desc"})
    except Exception as exc:
        result = [
            {"id": uid, "email": info["email"], "name": info["name"], "role": info["role"],
             "modules_completed": 0, "study_days": 0, "last_activity": None}
            for uid, info in users.items()
        ]
        return jsonify({"students": result, "warning": f"Progresso indisponível: {exc}"})

    prog_map  = defaultdict(list)
    study_map = defaultdict(list)

    for row in progress:
        prog_map[row["user_id"]].append(row)
    for row in study:
        study_map[row["user_id"]].append(row["day"])

    result = []
    for uid, info in users.items():
        result.append({
            "id": uid, "email": info["email"], "name": info["name"], "role": info["role"],
            "modules_completed": sum(1 for p in prog_map[uid] if p["completed"] > 0),
            "study_days":        len(study_map[uid]),
            "last_activity":     prog_map[uid][0]["updated_at"] if prog_map[uid] else None,
        })

    result.sort(key=lambda x: x["last_activity"] or "", reverse=True)
    return jsonify({"students": result})


@bp.get("/teacher/student/<user_id>/access")
def teacher_student_access(user_id: str):
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{user_id}"})
        return jsonify({"slugs": [r["module_slug"] for r in rows]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.put("/teacher/student/<user_id>/access")
def teacher_sync_access(user_id: str):
    if err := require_teacher_token():
        return err
    body  = request.get_json(silent=True) or {}
    slugs = [s.strip() for s in body.get("slugs", []) if s.strip()]
    supabase_url = current_app.config["SUPABASE_URL"]

    r = http.delete(
        f"{supabase_url}/rest/v1/student_access",
        headers=sb_headers(),
        params={"user_id": f"eq.{user_id}"},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.text}), r.status_code

    if slugs:
        rows = [{"user_id": user_id, "module_slug": s} for s in slugs]
        r = http.post(
            f"{supabase_url}/rest/v1/student_access",
            headers={**sb_headers(), "Prefer": "return=minimal"},
            json=rows,
            timeout=10,
        )
        if not r.ok:
            return jsonify({"error": r.text}), r.status_code

    return jsonify({"slugs": slugs})


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
    sb_delete("teacher_comments", {"id": f"eq.{comment_id}"})
    return "", 204


@bp.get("/teacher/student/<user_id>")
def teacher_student_detail(user_id: str):
    if err := require_teacher_token():
        return err
    try:
        progress = sb_get("module_progress",  {"select": "module_slug,completed,updated_at", "user_id": f"eq.{user_id}", "order": "updated_at.desc"})
        study    = sb_get("study_days",       {"select": "day", "user_id": f"eq.{user_id}", "order": "day.desc"})
        comments = sb_get("teacher_comments", {"select": "id,module_slug,content,created_at", "student_id": f"eq.{user_id}", "order": "created_at.desc"})
        supabase_url = current_app.config["SUPABASE_URL"]
        r_quiz = http.get(
            f"{supabase_url}/rest/v1/quiz_answers",
            headers=sb_headers(),
            params={"select": "module_slug,question,correct", "user_id": f"eq.{user_id}"},
            timeout=10,
        )
        quiz_rows = r_quiz.json() if r_quiz.ok else []
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    from collections import Counter
    total_q   = len(quiz_rows)
    correct_q = sum(1 for q in quiz_rows if q.get("correct"))
    wrong     = [q["question"] for q in quiz_rows if not q.get("correct") and q.get("question")]
    top_errors = [{"question": q, "count": c} for q, c in Counter(wrong).most_common(10)]

    return jsonify({
        "progress":      progress,
        "study_days":    [r["day"] for r in study],
        "comments":      comments,
        "extra_lessons": get_student_extra_lessons(user_id),
        "quiz": {
            "total":     total_q,
            "correct":   correct_q,
            "accuracy":  round(correct_q / total_q * 100) if total_q > 0 else None,
            "top_errors": top_errors,
        },
    })


@bp.get("/teacher/report")
def teacher_period_report():
    if err := require_teacher_token():
        return err

    start = request.args.get("start", "").strip()
    end   = request.args.get("end",   "").strip()
    if not start or not end:
        return jsonify({"error": "Parâmetros start e end são obrigatórios"}), 400

    supabase_url = current_app.config["SUPABASE_URL"]

    r = http.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        params={"per_page": 200},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"students": []})

    users_raw = r.json().get("users", [])
    users = {
        u["id"]: {
            "email": u["email"],
            "name":  (u.get("user_metadata") or {}).get("name") or "",
            "role":  (u.get("user_metadata") or {}).get("role") or "",
        }
        for u in users_raw
    }

    end_ts = f"{end}T23:59:59"
    try:
        r_study = http.get(
            f"{supabase_url}/rest/v1/study_days",
            headers=sb_headers(),
            params=[("select", "user_id,day"), ("day", f"gte.{start}"), ("day", f"lte.{end}")],
            timeout=10,
        )
        r_study.raise_for_status()

        r_prog = http.get(
            f"{supabase_url}/rest/v1/module_progress",
            headers=sb_headers(),
            params=[("select", "user_id,module_slug,updated_at"), ("completed", "gt.0"),
                    ("updated_at", f"gte.{start}"), ("updated_at", f"lte.{end_ts}")],
            timeout=10,
        )
        r_prog.raise_for_status()

        r_quiz = http.get(
            f"{supabase_url}/rest/v1/quiz_answers",
            headers=sb_headers(),
            params=[("select", "user_id,question,correct"),
                    ("created_at", f"gte.{start}"), ("created_at", f"lte.{end_ts}")],
            timeout=10,
        )
        r_quiz.raise_for_status()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    from collections import defaultdict, Counter
    study_map = defaultdict(list)
    prog_map  = defaultdict(list)
    quiz_map  = defaultdict(list)

    for row in r_study.json():
        study_map[row["user_id"]].append(row["day"])
    for row in r_prog.json():
        prog_map[row["user_id"]].append(row)
    for row in r_quiz.json():
        quiz_map[row["user_id"]].append(row)

    result = []
    for uid, info in users.items():
        if info["role"] == "teacher":
            continue
        quiz_user = quiz_map[uid]
        total_q   = len(quiz_user)
        correct_q = sum(1 for q in quiz_user if q.get("correct"))
        wrong     = [q["question"] for q in quiz_user if not q.get("correct") and q.get("question")]
        top_errors = [{"question": q, "count": c} for q, c in Counter(wrong).most_common(5)]
        result.append({
            "id":                uid,
            "email":             info["email"],
            "name":              info["name"],
            "study_days":        len(study_map[uid]),
            "modules_completed": len(prog_map[uid]),
            "modules":           [p["module_slug"] for p in prog_map[uid]],
            "quiz_total":        total_q,
            "quiz_correct":      correct_q,
            "quiz_accuracy":     round(correct_q / total_q * 100) if total_q > 0 else None,
            "top_errors":        top_errors,
        })

    result.sort(key=lambda x: x["study_days"], reverse=True)
    return jsonify({"students": result, "period": {"start": start, "end": end}})


@bp.get("/teacher/student/<user_id>/exercises")
def teacher_student_exercises(user_id: str):
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.get(
        f"{supabase_url}/rest/v1/quiz_answers",
        headers=sb_headers(),
        params={"select": "id,module_slug,step_index,step_kind,question,answer,correct,created_at",
                "user_id": f"eq.{user_id}", "order": "created_at.desc"},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": f"Supabase {r.status_code}: {r.text}", "exercises": []}), 500
    return jsonify({"exercises": r.json()})


@bp.get("/teacher/student/<user_id>/submissions")
def teacher_student_submissions(user_id: str):
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("submissions", {"select": "id,module_slug,audio_path,status,created_at",
                                      "user_id": f"eq.{user_id}", "order": "created_at.desc"})
        return jsonify({"submissions": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


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


@bp.get("/my-extra-lessons")
def my_extra_lessons():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({}), 401
    return jsonify(get_student_extra_lessons(user_id))


@bp.post("/teacher/student/<user_id>/extra-lessons")
def teacher_add_extra_lesson(user_id: str):
    if err := require_teacher_token():
        return err
    body = request.get_json(silent=True) or {}
    if not all(body.get(k) for k in ("module_slug", "title", "type", "url")):
        abort(400)
    lesson = add_student_extra_lesson(
        user_id=user_id,
        module_slug=body["module_slug"],
        title=body["title"],
        description=body.get("description", ""),
        content_type=body["type"],
        url=body["url"],
    )
    return jsonify(lesson), 201


@bp.delete("/teacher/student/<user_id>/extra-lessons/<lesson_id>")
def teacher_delete_extra_lesson(user_id: str, lesson_id: str):
    if err := require_teacher_token():
        return err
    if not delete_student_extra_lesson(user_id, lesson_id):
        abort(404)
    return "", 204


# ── API Admin ─────────────────────────────────────────────────────────────────

@bp.post("/admin/create-user")
def admin_create_user():
    if err := require_teacher_token():
        return err
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip()
    password = body.get("password", "").strip()
    name     = body.get("name", "").strip()
    role     = body.get("role", "aluno").strip()
    if not email or not password:
        abort(400)
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.post(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        json={"email": email, "password": password,
              "user_metadata": {"name": name, "role": role},
              "email_confirm": True},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify(r.json()), 201


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    from datetime import date
    return date.today().isoformat()
