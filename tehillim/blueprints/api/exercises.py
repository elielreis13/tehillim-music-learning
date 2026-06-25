from __future__ import annotations

from flask import jsonify, request, session

from . import bp
from tehillim.extensions import (
    sb_get, sb_post, sb_upsert, sb_delete,
    require_teacher_token, get_student_teacher_id,
)
from tehillim.content import (
    get_student_extra_lessons, add_student_extra_lesson, delete_student_extra_lesson,
)
from .progress import _today


def _fetch_standalone_for_student(user_id: str) -> list:
    """Return standalone exercises visible to this student, with completion flag."""
    try:
        teacher_id = get_student_teacher_id(user_id)

        # Always fetch exercises specifically assigned to this student
        specific = sb_get("standalone_assignments", {
            "select":     "exercise_id",
            "student_id": f"eq.{user_id}",
        })
        specific_ids = {a["exercise_id"] for a in specific}

        # If we know the teacher, also fetch "all students" assignments from that teacher
        all_ids: set = set()
        if teacher_id:
            all_asgn = sb_get("standalone_assignments", {
                "select":     "exercise_id",
                "student_id": "is.null",
            })
            candidate_ids = [a["exercise_id"] for a in all_asgn]
            if candidate_ids:
                teacher_exs = sb_get("standalone_exercises", {
                    "select":     "id",
                    "teacher_id": f"eq.{teacher_id}",
                    "id":         f"in.({','.join(candidate_ids)})",
                })
                all_ids = {e["id"] for e in teacher_exs}

        combined_ids = list(specific_ids | all_ids)
        if not combined_ids:
            return []

        exercises = sb_get("standalone_exercises", {
            "select": "id,title,prompt,game_kind,game_data",
            "id":     f"in.({','.join(combined_ids)})",
            "order":  "created_at.asc",
        })
        if not exercises:
            return []

        done_rows = sb_get("standalone_completions", {
            "select":      "exercise_id",
            "student_id":  f"eq.{user_id}",
            "exercise_id": f"in.({','.join(e['id'] for e in exercises)})",
        })
        done_ids = {d["exercise_id"] for d in done_rows}

        return [
            {**ex, "completed": ex["id"] in done_ids, "type": "standalone"}
            for ex in exercises
        ]
    except Exception:
        return []


@bp.get("/games/demo")
def games_demo():
    from tehillim.content.demo_games import DEMO_GAMES
    return jsonify({"games": DEMO_GAMES})


@bp.post("/admin/jogos")
def admin_jogos_create():
    if err := require_teacher_token():
        return err
    data = request.get_json(silent=True) or {}
    required = ("module_slug", "title", "game_kind")
    if any(f not in data or not data[f] for f in required):
        return jsonify({"error": "Preencha: módulo, título e tipo de jogo."}), 400
    import json as _json, re as _re
    _UUID_RE = _re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.I)
    def _safe_uuid(v):
        return v if (v and _UUID_RE.match(str(v))) else None
    try:
        existing = sb_get("module_games", {
            "select": "order_index",
            "module_slug": f"eq.{data['module_slug']}",
            "order": "order_index.desc",
            "limit": "1",
        })
        next_index = (existing[0]["order_index"] + 1) if existing else 0
        game_data = data.get("game_data", {})
        payload = {
            "module_slug":  data["module_slug"],
            "title":        data["title"],
            "description":  data.get("description", ""),
            "game_kind":    data["game_kind"],
            "body":         data.get("body", ""),
            "game_data":    game_data,
            "order_index":  next_index,
            "created_by":   _safe_uuid(session.get("user_id")),
        }
        try:
            row = sb_post("module_games", payload)
        except Exception as first_exc:
            # game_data column may not exist yet — retry without it
            if "game_data" in str(first_exc):
                payload.pop("game_data")
                payload["body"] = _json.dumps(game_data, ensure_ascii=False)
                row = sb_post("module_games", payload)
            else:
                raise
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    created = row[0] if isinstance(row, list) else row
    return jsonify({"game": created}), 201


@bp.delete("/admin/jogos/<game_id>")
def admin_jogos_delete(game_id: str):
    if err := require_teacher_token():
        return err
    try:
        sb_delete("module_games", {"id": f"eq.{game_id}"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True})


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
        from flask import abort
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
        from flask import abort
        abort(404)
    return "", 204


@bp.get("/exercises-by-module")
def exercises_by_module():
    """Per-module exercise list for the student exercise page."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    import hashlib
    today = _today()

    try:
        completed = sb_get("module_progress", {
            "select":    "module_slug,completed_at",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
            "order":     "completed_at.asc",
        })
    except Exception:
        completed = []

    if not completed:
        return jsonify({"modules": []})

    completed_slugs = [r["module_slug"] for r in completed]

    # Which modules have been exercised today?
    try:
        done_today = sb_get("daily_completions", {
            "select":        "module_slug",
            "user_id":       f"eq.{user_id}",
            "exercise_date": f"eq.{today}",
        })
        done_today_slugs = {r["module_slug"] for r in done_today}
    except Exception:
        done_today_slugs = set()

    from tehillim.content import get_module

    result = []
    for slug in completed_slugs:
        mod = get_module(slug)
        if not mod:
            continue

        exercises = [
            {
                "index":   i,
                "kind":    s.kind,
                "prompt":  s.prompt,
                "options": list(s.options),
                "answer":  s.answer,
            }
            for i, s in enumerate(mod.steps)
            if s.kind in ("exercise-mc", "exercise-tf", "exercise-fill") and s.options
        ]
        if not exercises:
            continue

        seed = int(hashlib.md5(f"{user_id}:{slug}:{today}".encode()).hexdigest(), 16)
        today_local = seed % len(exercises)

        result.append({
            "module_slug":       slug,
            "module_title":      mod.title,
            "module_number":     mod.number,
            "exercises":         exercises,
            "today_local_index": today_local,
            "completed_today":   slug in done_today_slugs,
        })

    return jsonify({"modules": result})


@bp.get("/exercises-week")
def exercises_week():
    """Return the current week (Mon–Sun) with exercises per day, grouped by module."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    import hashlib
    from datetime import date, timedelta

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    # ── Standalone exercises (fetched first, independent of modules) ──────────────
    standalone_today = _fetch_standalone_for_student(user_id)

    # ── Module completions ────────────────────────────────────────────────────────
    try:
        completed = sb_get("module_progress", {
            "select":    "module_slug,completed_at",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
            "order":     "completed_at.asc",
        })
    except Exception:
        completed = []

    if not completed:
        # No modules yet — still return week skeleton with standalone in today's slot
        if not standalone_today:
            return jsonify({"days": [], "has_modules": False})
        DAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        DAYS_FULL  = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        days = []
        for d in week_dates:
            d_str = str(d); weekday = d.weekday()
            is_today_f = d == today
            cards = standalone_today if is_today_f else []
            days.append({
                "date": d_str, "day_short": DAYS_SHORT[weekday], "day_full": DAYS_FULL[weekday],
                "day_num": d.day, "is_today": is_today_f, "is_past": d < today, "is_future": d > today,
                "cards": [] if d > today else cards,
                "completed_count": sum(1 for c in cards if c.get("completed")),
                "total_count": len(cards),
            })
        return jsonify({"days": days, "has_modules": True})

    completed_slugs = [r["module_slug"] for r in completed]

    # Completions for the entire current week
    try:
        done_rows = sb_get("daily_completions", {
            "select":        "exercise_date,module_slug",
            "user_id":       f"eq.{user_id}",
            "exercise_date": f"gte.{monday}",
        })
        done_set = {(r["exercise_date"], r["module_slug"]) for r in done_rows}
    except Exception:
        done_set = set()

    from tehillim.content import get_module
    from datetime import datetime

    module_exercises: dict = {}
    for r in completed:
        slug = r["module_slug"]
        # Parse the date the module was completed so we can gate exercises.
        raw_ts = r.get("completed_at") or ""
        try:
            completed_date = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).date()
        except Exception:
            from datetime import date as _date
            completed_date = _date(2000, 1, 1)

        mod = get_module(slug)
        if not mod:
            continue
        exercises = [
            {
                "index":   i,
                "kind":    s.kind,
                "prompt":  s.prompt,
                "options": list(s.options),
                "answer":  s.answer,
            }
            for i, s in enumerate(mod.steps)
            if s.kind in ("exercise-mc", "exercise-tf", "exercise-fill") and s.options
        ]
        if exercises:
            module_exercises[slug] = {
                "slug":           slug,
                "title":          mod.title,
                "number":         mod.number,
                "exercises":      exercises,
                "completed_date": completed_date,
            }

    if not module_exercises and not standalone_today:
        return jsonify({"days": [], "has_modules": False})

    DAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    DAYS_FULL  = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

    days = []
    for d in week_dates:
        d_str   = str(d)
        weekday = d.weekday()
        is_past    = d < today
        is_future  = d > today
        is_today_f = d == today

        day_modules = []
        for slug, m in module_exercises.items():
            if m["completed_date"] > d:
                continue

            seed   = int(hashlib.md5(f"{user_id}:{slug}:{d_str}".encode()).hexdigest(), 16)
            ex_idx = seed % len(m["exercises"])
            ex     = m["exercises"][ex_idx]
            completed_flag = (d_str, slug) in done_set
            day_modules.append({
                "module_slug":   slug,
                "module_title":  m["title"],
                "module_number": m["number"],
                "exercise":      ex,
                "exercise_index": ex_idx,
                "completed":     completed_flag,
            })

        day_modules.sort(key=lambda x: x["module_number"])
        cards = day_modules
        completed_count = sum(1 for c in cards if c.get("completed"))
        total = len(cards)

        days.append({
            "date":            d_str,
            "day_short":       DAYS_SHORT[weekday],
            "day_full":        DAYS_FULL[weekday],
            "day_num":         d.day,
            "is_today":        is_today_f,
            "is_past":         is_past,
            "is_future":       is_future,
            "cards":           [] if is_future else cards,
            "completed_count": 0 if is_future else completed_count,
            "total_count":     total,
        })

    return jsonify({
        "days":       days,
        "has_modules": True,
        "standalone": standalone_today,
    })


@bp.get("/standalone-exercises")
def get_standalone_exercises():
    """Return exercises assigned to the current student (pending + completed)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    teacher_id = get_student_teacher_id(user_id)
    if not teacher_id:
        return jsonify({"exercises": []})

    try:
        # assignments for this student (null student_id = all students of teacher)
        assignments = sb_get("standalone_assignments", {
            "select": "exercise_id",
            "or":     f"(student_id.eq.{user_id},student_id.is.null)",
        })
        # filter only assignments from this student's teacher
        ex_ids = [a["exercise_id"] for a in assignments]
        if not ex_ids:
            return jsonify({"exercises": []})

        exercises = sb_get("standalone_exercises", {
            "select":     "id,title,prompt,game_kind,game_data,created_at",
            "teacher_id": f"eq.{teacher_id}",
            "id":         f"in.({','.join(ex_ids)})",
            "order":      "created_at.desc",
        })
    except Exception:
        return jsonify({"exercises": []})

    if not exercises:
        return jsonify({"exercises": []})

    # Which ones has this student completed?
    try:
        done = sb_get("standalone_completions", {
            "select":      "exercise_id",
            "student_id":  f"eq.{user_id}",
            "exercise_id": f"in.({','.join(e['id'] for e in exercises)})",
        })
        done_ids = {d["exercise_id"] for d in done}
    except Exception:
        done_ids = set()

    for ex in exercises:
        ex["completed"] = ex["id"] in done_ids

    return jsonify({"exercises": exercises})


@bp.post("/standalone-exercises/<ex_id>/complete")
def complete_standalone_exercise(ex_id: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        sb_upsert("standalone_completions", {
            "exercise_id": ex_id,
            "student_id":  user_id,
        }, conflict_col="exercise_id,student_id")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@bp.get("/teacher/standalone-exercises")
def teacher_list_standalone_exercises():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        exercises = sb_get("standalone_exercises", {
            "select": "id,title,prompt,game_kind,game_data,created_at",
            "teacher_id": f"eq.{teacher_id}",
            "order": "created_at.desc",
        })
    except Exception:
        exercises = []
    return jsonify({"exercises": exercises})


@bp.post("/teacher/standalone-exercises")
def teacher_create_standalone_exercise():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    body = request.get_json(silent=True) or {}

    title     = (body.get("title") or "").strip()
    prompt    = (body.get("prompt") or "").strip()
    game_kind = (body.get("game_kind") or "").strip()
    game_data = body.get("game_data") or {}
    assign_to = body.get("assign_to") or []  # list of student_ids, or [] = all

    if not title or not game_kind:
        return jsonify({"error": "Campos obrigatórios: título e tipo de jogo."}), 400

    try:
        rows = sb_post("standalone_exercises", {
            "teacher_id": teacher_id,
            "title":      title,
            "prompt":     prompt,
            "game_kind":  game_kind,
            "game_data":  game_data,
        })
        ex_id = rows[0]["id"] if rows else None
        if not ex_id:
            raise Exception("no id returned")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Create assignments
    try:
        if assign_to:
            for sid in assign_to:
                sb_post("standalone_assignments", {
                    "exercise_id": ex_id,
                    "student_id":  sid,
                })
        else:
            # null student_id = all students
            sb_post("standalone_assignments", {
                "exercise_id": ex_id,
                "student_id":  None,
            })
    except Exception:
        pass

    return jsonify({"ok": True, "id": ex_id}), 201


@bp.delete("/teacher/standalone-exercises/<ex_id>")
def teacher_delete_standalone_exercise(ex_id: str):
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        sb_delete("standalone_exercises", {
            "id":         f"eq.{ex_id}",
            "teacher_id": f"eq.{teacher_id}",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@bp.get("/teacher/standalone-exercises/<ex_id>/responses")
def teacher_standalone_responses(ex_id: str):
    if err := require_teacher_token():
        return err
    try:
        completions = sb_get("standalone_completions", {
            "select":      "student_id,completed_at",
            "exercise_id": f"eq.{ex_id}",
        })
    except Exception:
        completions = []

    # Enrich with student names (best-effort)
    from flask import current_app
    import requests as http
    from tehillim.extensions import sb_headers
    try:
        supabase_url = current_app.config["SUPABASE_URL"]
        r = http.get(
            f"{supabase_url}/auth/v1/admin/users",
            headers=sb_headers(),
            params={"per_page": 200},
            timeout=8,
        )
        users_map = {}
        if r.ok:
            for u in r.json().get("users", []):
                name = (u.get("user_metadata") or {}).get("name") or u.get("email", u["id"])
                users_map[u["id"]] = name
    except Exception:
        users_map = {}

    result = []
    for c in completions:
        result.append({
            "student_id":   c["student_id"],
            "student_name": users_map.get(c["student_id"], c["student_id"]),
            "completed_at": c["completed_at"],
        })

    return jsonify({"responses": result})
