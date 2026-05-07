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
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({
        "progress":     progress,
        "study_days":   [r["day"] for r in study],
        "comments":     comments,
        "extra_lessons": get_student_extra_lessons(user_id),
    })


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
