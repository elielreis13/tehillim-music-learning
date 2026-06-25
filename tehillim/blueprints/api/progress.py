from __future__ import annotations

from flask import abort, current_app, jsonify, request, session

from . import bp
from tehillim.extensions import (
    sb_get, sb_headers, sb_post, sb_put, sb_upsert,
    get_student_teacher_id,
)
import requests as _http


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


def _this_week_monday() -> str:
    from datetime import date, timedelta
    d = date.today()
    return (d - timedelta(days=d.weekday())).isoformat()


def _schedule_spaced_reviews(user_id: str, module_slug: str, completed_at_iso: str):
    """Creates spaced review entries at +2, +7, +14, +30 days."""
    from datetime import datetime, timezone, timedelta
    try:
        teacher_id = get_student_teacher_id(user_id) or ""
        base_dt = datetime.fromisoformat(completed_at_iso.replace("Z", "+00:00"))
        for days in (2, 7, 14, 30):
            scheduled = (base_dt + timedelta(days=days)).date().isoformat()
            try:
                sb_upsert("spaced_reviews", {
                    "user_id":        user_id,
                    "teacher_id":     teacher_id,
                    "module_slug":    module_slug,
                    "scheduled_date": scheduled,
                }, conflict_col="user_id,module_slug,scheduled_date")
            except Exception:
                pass
    except Exception:
        pass


def _pick_daily_exercise(user_id: str, today: str) -> dict | None:
    """Returns a deterministic exercise for user+date, from completed modules."""
    import hashlib
    from tehillim.content import get_module

    try:
        completed = sb_get("module_progress", {
            "select":    "module_slug",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
        })
    except Exception:
        return None

    if not completed:
        return None

    completed_slugs = [r["module_slug"] for r in completed]

    # Collect all exercises across completed modules
    all_exercises = []
    for slug in completed_slugs:
        mod = get_module(slug)
        if not mod:
            continue
        for i, step in enumerate(mod.steps):
            if step.kind in ("exercise-mc", "exercise-tf", "exercise-fill") and step.options:
                all_exercises.append({
                    "module_slug":  slug,
                    "module_title": mod.title,
                    "exercise_index": i,
                    "kind":    step.kind,
                    "prompt":  step.prompt,
                    "options": list(step.options),
                    "answer":  step.answer,
                })

    if not all_exercises:
        return None

    seed = int(hashlib.md5(f"{user_id}:{today}".encode()).hexdigest(), 16)
    return all_exercises[seed % len(all_exercises)]


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

    now = _now_iso()
    payload = {"user_id": user_id, "module_slug": module_slug,
               "completed": completed, "updated_at": now}

    # Set completed_at only on first completion (preserved via upsert logic)
    first_completion = False
    if completed > 0:
        existing = sb_get("module_progress", {
            "select": "completed,completed_at",
            "user_id": f"eq.{user_id}",
            "module_slug": f"eq.{module_slug}",
        })
        prev_completed = existing[0].get("completed", 0) if existing else 0
        prev_completed_at = existing[0].get("completed_at") if existing else None
        if not prev_completed_at:
            payload["completed_at"] = now
            if prev_completed == 0:
                first_completion = True

    try:
        sb_upsert("module_progress", payload, conflict_col="user_id,module_slug")
    except Exception:
        try:
            sb_post("module_progress", payload)
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


@bp.post("/me/avatar")
def update_avatar():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    avatar_id = (request.get_json(silent=True) or {}).get("avatar_id", "").strip()
    if not avatar_id:
        abort(400)
    try:
        sb_put(f"/auth/v1/admin/users/{user_id}", {"user_metadata": {"avatar": avatar_id, "avatar_url": None}})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True})


@bp.post("/me/photo")
def update_photo():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
    content_type = (f.content_type or "image/jpeg").split(";")[0].strip()
    if content_type not in allowed:
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400
    ext_map = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}
    ext = ext_map.get(content_type, "jpg")
    filename = f"{user_id}.{ext}"
    supabase_url = current_app.config["SUPABASE_URL"]
    service_key  = current_app.config["SUPABASE_SERVICE_KEY"]
    upload_url = f"{supabase_url}/storage/v1/object/avatars/{filename}"
    r = _http.post(upload_url, headers={
        "apikey":        service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type":  content_type,
        "x-upsert":      "true",
    }, data=f.read(), timeout=30)
    if not r.ok:
        return jsonify({"error": f"Storage: {r.status_code} {r.text}"}), 500
    public_url = f"{supabase_url}/storage/v1/object/public/avatars/{filename}"
    try:
        sb_put(f"/auth/v1/admin/users/{user_id}", {"user_metadata": {"avatar_url": public_url, "avatar": None}})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True, "url": public_url})


@bp.post("/me/password")
def update_password():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    password = (request.get_json(silent=True) or {}).get("password", "")
    if len(password) < 8:
        return jsonify({"error": "Senha muito curta"}), 400
    try:
        sb_put(f"/auth/v1/admin/users/{user_id}", {"password": password})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True})


@bp.get("/me/profile")
def get_profile():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        r = _http.get(
            f"{current_app.config['SUPABASE_URL']}/auth/v1/admin/users/{user_id}",
            headers=sb_headers(), timeout=5,
        )
        meta = r.json().get("user_metadata") or {} if r.ok else {}
    except Exception:
        meta = {}
    return jsonify({
        "name":       session.get("name", ""),
        "email":      session.get("email", ""),
        "avatar":     meta.get("avatar"),
        "avatar_url": meta.get("avatar_url"),
    })


@bp.get("/daily-exercise")
def get_daily_exercise():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    from datetime import date, timedelta

    today_str = _today()
    today_date = date.today()

    # Find first module completion to anchor the lookback window
    try:
        first_rows = sb_get("module_progress", {
            "select":    "completed_at",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
            "order":     "completed_at.asc",
            "limit":     "1",
        })
        first_completion = first_rows[0]["completed_at"][:10] if first_rows else None
    except Exception:
        first_completion = None

    if not first_completion:
        return jsonify({"available": False})

    # Lookback: from first completion (max 14 days ago) to today
    lookback_start = max(
        date.fromisoformat(first_completion),
        today_date - timedelta(days=14),
    )

    # Dates that should have a completion
    all_dates = []
    d = lookback_start
    while d <= today_date:
        all_dates.append(d.isoformat())
        d += timedelta(days=1)

    # Fetch which dates are already completed
    try:
        done_rows = sb_get("daily_completions", {
            "select":        "exercise_date",
            "user_id":       f"eq.{user_id}",
            "exercise_date": f"gte.{lookback_start.isoformat()}",
        })
        done_dates = {r["exercise_date"] for r in done_rows}
    except Exception:
        done_dates = set()

    pending_dates = [d for d in all_dates if d not in done_dates]
    pending_count = len(pending_dates)

    if not pending_dates:
        return jsonify({"available": True, "completed": True, "pending_count": 0})

    # Serve the oldest pending date's exercise
    target_date = pending_dates[0]
    exercise = _pick_daily_exercise(user_id, target_date)
    if not exercise:
        return jsonify({"available": False})

    return jsonify({
        "available":       True,
        "completed":       False,
        "pending_count":   pending_count,
        "exercise_date":   target_date,
        "module_slug":     exercise["module_slug"],
        "module_title":    exercise["module_title"],
        "exercise_index":  exercise["exercise_index"],
        "kind":            exercise["kind"],
        "prompt":          exercise["prompt"],
        "options":         exercise["options"],
        "answer":          exercise["answer"],
    })


@bp.post("/daily-exercise/complete")
def complete_daily_exercise():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    body = request.get_json(silent=True) or {}
    exercise_date = body.get("exercise_date") or _today()
    try:
        sb_upsert("daily_completions", {
            "user_id":        user_id,
            "exercise_date":  exercise_date,
            "module_slug":    body.get("module_slug", ""),
            "exercise_index": body.get("exercise_index", 0),
        }, conflict_col="user_id,exercise_date,module_slug")
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.get("/reviews")
def get_reviews():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    from datetime import date, timedelta
    from tehillim.content import get_module

    today        = date.today()
    this_monday  = _this_week_monday()
    next_monday  = (today - timedelta(days=today.weekday()) + timedelta(weeks=1)).isoformat()

    # ── Gate: check for pending daily exercises since this Monday ─────────────
    # All days from this_monday (inclusive) to yesterday must have a completion.
    gate_start = date.fromisoformat(this_monday)
    gate_dates = []
    d = gate_start
    while d < today:
        gate_dates.append(d.isoformat())
        d += timedelta(days=1)

    if gate_dates:
        try:
            done_daily = sb_get("daily_completions", {
                "select":        "exercise_date",
                "user_id":       f"eq.{user_id}",
                "exercise_date": f"gte.{this_monday}",
            })
            done_daily_dates = {r["exercise_date"] for r in done_daily}
        except Exception:
            done_daily_dates = set()

        # Only count days where the student had at least one completed module
        try:
            first_rows = sb_get("module_progress", {
                "select":    "completed_at",
                "user_id":   f"eq.{user_id}",
                "completed": "gt.0",
                "order":     "completed_at.asc",
                "limit":     "1",
            })
            first_completion = first_rows[0]["completed_at"][:10] if first_rows else None
        except Exception:
            first_completion = None

        if first_completion:
            pending_daily = [
                dt for dt in gate_dates
                if dt >= first_completion and dt not in done_daily_dates
            ]
        else:
            pending_daily = []

        if pending_daily:
            return jsonify({
                "blocked":        True,
                "pending_daily":  len(pending_daily),
                "this_week":      [],
                "next_monday":    next_monday,
            })

    # ── Normal review logic ───────────────────────────────────────────────────
    min_age = today - timedelta(days=7)   # completed at least 7 days ago
    max_age = today - timedelta(days=60)  # ignore older than 60 days

    try:
        progress = sb_get("module_progress", {
            "select":       "module_slug,completed_at",
            "user_id":      f"eq.{user_id}",
            "completed":    "gt.0",
            "completed_at": f"gte.{max_age.isoformat()}",
        })
    except Exception:
        progress = []

    eligible = [
        p for p in progress
        if p.get("completed_at") and p["completed_at"][:10] <= min_age.isoformat()
    ]

    if not eligible:
        return jsonify({"this_week": [], "next_monday": next_monday})

    try:
        done = sb_get("review_completions", {
            "select":        "module_slug",
            "user_id":       f"eq.{user_id}",
            "reviewed_week": f"eq.{this_monday}",
        })
        done_slugs = {d["module_slug"] for d in done}
    except Exception:
        done_slugs = set()

    pending = []
    for p in eligible:
        slug = p["module_slug"]
        if slug in done_slugs:
            continue
        mod = get_module(slug)
        pending.append({
            "id":           slug,
            "module_slug":  slug,
            "module_title": mod.title if mod else slug,
            "completed_at": p["completed_at"],
        })

    return jsonify({"this_week": pending, "next_monday": next_monday})


@bp.post("/reviews/<module_slug>/complete")
def complete_review(module_slug: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        sb_upsert("review_completions", {
            "user_id":       user_id,
            "module_slug":   module_slug,
            "reviewed_week": _this_week_monday(),
        }, conflict_col="user_id,module_slug,reviewed_week")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@bp.get("/reviews/<module_slug>/exercise")
def get_review_exercise(module_slug: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    from tehillim.content import get_module
    mod = get_module(module_slug)
    if not mod:
        return jsonify({"error": "Módulo não encontrado"}), 404

    exercises = [s for s in mod.steps if s.kind.startswith("exercise-") and s.kind != "exercise-match"]
    if not exercises:
        return jsonify({"available": False})

    # Deterministic by module + current week
    import hashlib
    seed = int(hashlib.md5(f"{module_slug}:{_this_week_monday()}".encode()).hexdigest(), 16)
    ex = exercises[seed % len(exercises)]
    return jsonify({
        "available":    True,
        "module_slug":  module_slug,
        "module_title": mod.title,
        "kind":         ex.kind,
        "prompt":       ex.prompt,
        "options":      list(ex.options),
        "answer":       ex.answer,
    })


@bp.get("/module-unlock-status")
def module_unlock_status():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    # Read lock_days from teacher settings (default 3)
    LOCK_DAYS = 3
    teacher_id = get_student_teacher_id(user_id)
    if teacher_id:
        try:
            rows = sb_get("teacher_settings", {
                "select":     "value",
                "teacher_id": f"eq.{teacher_id}",
                "key":        "eq.module_lock_days",
            })
            if rows:
                LOCK_DAYS = max(0, int(rows[0]["value"]))
        except Exception:
            pass

    if LOCK_DAYS == 0:
        # Lock disabled — return everything as unlocked
        from tehillim.content.groups import GROUPS
        return jsonify({mod.slug: {"locked": False} for g in GROUPS for mod in g.modules})

    try:
        progress = sb_get("module_progress", {
            "select":   "module_slug,completed,completed_at",
            "user_id":  f"eq.{user_id}",
            "completed": "gt.0",
        })
    except Exception:
        progress = []

    # Map slug → completed_at
    completed_map = {p["module_slug"]: p.get("completed_at") for p in progress}

    from tehillim.content.groups import GROUPS
    from datetime import datetime, timezone, timedelta

    result = {}
    for group in GROUPS:
        mods = list(group.modules)
        for i, mod in enumerate(mods):
            if i == 0:
                result[mod.slug] = {"locked": False}
                continue
            prev = mods[i - 1]
            prev_completed_at = completed_map.get(prev.slug)
            if not prev_completed_at:
                # Previous not completed → locked
                result[mod.slug] = {"locked": True, "reason": "prev_not_done"}
                continue
            try:
                completed_dt = datetime.fromisoformat(prev_completed_at.replace("Z", "+00:00"))
                unlock_dt = completed_dt + timedelta(days=LOCK_DAYS)
                now = datetime.now(timezone.utc)
                if now < unlock_dt:
                    result[mod.slug] = {
                        "locked": True,
                        "unlocks_at": unlock_dt.isoformat(),
                        "days_left": max(1, (unlock_dt - now).days + 1),
                    }
                else:
                    result[mod.slug] = {"locked": False}
            except Exception:
                result[mod.slug] = {"locked": False}

    return jsonify(result)
