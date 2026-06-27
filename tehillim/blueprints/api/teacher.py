from __future__ import annotations

from flask import current_app, jsonify, request, session
import requests as http

from . import bp
from tehillim.extensions import (
    sb_get, sb_headers, sb_post, sb_put, sb_upsert, sb_delete,
    require_teacher_token, is_owner_session, assert_student_owner,
    get_student_teacher_id,
)
from tehillim.content import get_student_extra_lessons
from .progress import _now_iso


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

    # Professores só vêem seus próprios alunos; owner vê todos
    if not is_owner_session():
        my_id = session.get("user_id")
        users_raw = [
            u for u in users_raw
            if (u.get("user_metadata") or {}).get("teacher_id") == my_id
        ]

    users = {
        u["id"]: {
            "email":      u["email"],
            "name":       (u.get("user_metadata") or {}).get("name") or "",
            "role":       (u.get("user_metadata") or {}).get("role") or "",
            "teacher_id": (u.get("user_metadata") or {}).get("teacher_id") or "",
        }
        for u in users_raw
    }

    try:
        progress = sb_get("module_progress", {"select": "user_id,module_slug,completed,updated_at", "order": "updated_at.desc"})
        study    = sb_get("study_days",      {"select": "user_id,day", "order": "day.desc"})
    except Exception as exc:
        result = [
            {"id": uid, "email": info["email"], "name": info["name"], "role": info["role"],
             "teacher_id": info["teacher_id"],
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
            "teacher_id":        info["teacher_id"],
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
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    try:
        rows = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{user_id}"})
        return jsonify({"slugs": [r["module_slug"] for r in rows]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.put("/teacher/student/<user_id>/access")
def teacher_sync_access(user_id: str):
    if err := require_teacher_token():
        return err
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
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


@bp.get("/teacher/student/<user_id>")
def teacher_student_detail(user_id: str):
    if err := require_teacher_token():
        return err
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
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
        rows = sb_get("submissions", {"select": "id,user_id,module_slug,audio_url,status,created_at",
                                      "user_id": f"eq.{user_id}", "order": "created_at.desc"})
        return jsonify({"submissions": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/teacher/submissions")
def teacher_all_submissions():
    """Todas as gravações dos alunos do professor, ordenadas por data."""
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("submissions", {"select": "id,user_id,module_slug,audio_url,status,created_at",
                                      "order": "created_at.desc", "limit": "200"})
        # Filtra só alunos do professor (se não for owner)
        if not is_owner_session():
            my_id = session.get("user_id")
            import requests as _http
            supabase_url = current_app.config["SUPABASE_URL"]
            r = _http.get(f"{supabase_url}/auth/v1/admin/users",
                          headers=sb_headers(), params={"per_page": 200}, timeout=10)
            if r.ok:
                my_student_ids = {
                    u["id"] for u in r.json().get("users", [])
                    if (u.get("user_metadata") or {}).get("teacher_id") == my_id
                }
                rows = [row for row in rows if row.get("user_id") in my_student_ids]
        return jsonify({"submissions": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/teacher/progress")
def teacher_all_progress():
    """Progresso de módulos de todos os alunos do professor."""
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("module_progress", {"select": "user_id,module_slug,completed,updated_at",
                                          "order": "updated_at.desc"})
        if not is_owner_session():
            my_id = session.get("user_id")
            import requests as _http
            supabase_url = current_app.config["SUPABASE_URL"]
            r = _http.get(f"{supabase_url}/auth/v1/admin/users",
                          headers=sb_headers(), params={"per_page": 200}, timeout=10)
            if r.ok:
                my_student_ids = {
                    u["id"] for u in r.json().get("users", [])
                    if (u.get("user_metadata") or {}).get("teacher_id") == my_id
                }
                rows = [row for row in rows if row.get("user_id") in my_student_ids]
        return jsonify({"progress": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/teacher/submissions/unread-count")
def teacher_submissions_unread_count():
    """Conta gravações enviadas desde a última vez que o professor abriu o dashboard."""
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        # Busca timestamp da última visualização
        rows = sb_get("teacher_settings", {"teacher_id": f"eq.{teacher_id}",
                                           "key": "eq.submissions_last_seen"})
        last_seen = rows[0]["value"] if rows else "1970-01-01T00:00:00Z"

        all_rows = sb_get("submissions", {"select": "id,user_id,created_at",
                                          "created_at": f"gt.{last_seen}",
                                          "order": "created_at.desc", "limit": "200"})
        if not is_owner_session():
            my_id = session.get("user_id")
            import requests as _http
            supabase_url = current_app.config["SUPABASE_URL"]
            r = _http.get(f"{supabase_url}/auth/v1/admin/users",
                          headers=sb_headers(), params={"per_page": 200}, timeout=10)
            if r.ok:
                my_student_ids = {
                    u["id"] for u in r.json().get("users", [])
                    if (u.get("user_metadata") or {}).get("teacher_id") == my_id
                }
                all_rows = [row for row in all_rows if row.get("user_id") in my_student_ids]
        return jsonify({"count": len(all_rows)})
    except Exception as exc:
        return jsonify({"count": 0, "error": str(exc)})


@bp.post("/teacher/submissions/mark-seen")
def teacher_submissions_mark_seen():
    """Marca o momento atual como 'visto' para zerar o badge de gravações."""
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        sb_upsert("teacher_settings", {
            "teacher_id": teacher_id,
            "key":        "submissions_last_seen",
            "value":      _now_iso(),
        }, conflict_col="teacher_id,key")
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.get("/teacher/settings")
def teacher_get_settings():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        rows = sb_get("teacher_settings", {"teacher_id": f"eq.{teacher_id}"})
        settings = {r["key"]: r["value"] for r in rows}
    except Exception:
        settings = {}
    return jsonify({"settings": settings})


@bp.post("/teacher/settings")
def teacher_save_settings():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    body = request.get_json(silent=True) or {}
    for key, value in body.items():
        try:
            sb_upsert("teacher_settings", {
                "teacher_id": teacher_id,
                "key":        str(key),
                "value":      str(value),
            }, conflict_col="teacher_id,key")
        except Exception:
            pass
    return jsonify({"ok": True})


@bp.get("/teacher/weekly-challenges")
def teacher_list_challenges():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        challenges = sb_get("weekly_challenges", {
            "select": "id,title,description,week_of,created_at",
            "teacher_id": f"eq.{teacher_id}",
            "order":      "week_of.desc",
        })
    except Exception:
        challenges = []
    return jsonify({"challenges": challenges})


@bp.post("/teacher/weekly-challenges")
def teacher_create_challenge():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    body = request.get_json(silent=True) or {}
    title       = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    if not title or not description:
        return jsonify({"error": "Título e descrição obrigatórios"}), 400

    from datetime import date
    today_d = date.today()
    week_of = (today_d - __import__('datetime').timedelta(days=today_d.weekday())).isoformat()

    try:
        saved = sb_post("weekly_challenges", {
            "teacher_id":  teacher_id,
            "title":       title,
            "description": description,
            "week_of":     week_of,
        })
        if isinstance(saved, list): saved = saved[0]
        return jsonify({"ok": True, "id": saved.get("id")}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/teacher/weekly-challenges/<challenge_id>/responses")
def teacher_challenge_responses(challenge_id: str):
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")

    # Verify challenge belongs to this teacher
    try:
        challenges = sb_get("weekly_challenges", {
            "select": "id,title",
            "id":         f"eq.{challenge_id}",
            "teacher_id": f"eq.{teacher_id}",
        })
        if not challenges:
            return jsonify({"error": "Não encontrado"}), 404

        responses = sb_get("challenge_responses", {
            "select": "student_id,response,created_at",
            "challenge_id": f"eq.{challenge_id}",
            "order":        "created_at.asc",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Enrich with student names
    supabase_url = current_app.config["SUPABASE_URL"]
    result = []
    for r in responses:
        name = r["student_id"]
        try:
            u = http.get(f"{supabase_url}/auth/v1/admin/users/{r['student_id']}",
                         headers=sb_headers(), timeout=5)
            if u.ok:
                meta = u.json().get("user_metadata") or {}
                name = meta.get("name") or u.json().get("email", r["student_id"])
        except Exception:
            pass
        result.append({"student_name": name, "response": r["response"], "created_at": r["created_at"]})

    return jsonify({"challenge": challenges[0], "responses": result})


@bp.post("/admin/create-user")
def admin_create_user():
    if err := require_teacher_token():
        return err
    body       = request.get_json(silent=True) or {}
    email      = body.get("email", "").strip()
    password   = body.get("password", "").strip()
    name       = body.get("name", "").strip()
    role       = body.get("role", "aluno").strip()
    teacher_id = session.get("user_id")
    if not email or not password:
        from flask import abort
        abort(400)
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.post(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        json={"email": email, "password": password,
              "user_metadata": {"name": name, "role": role, "teacher_id": teacher_id},
              "email_confirm": True},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify(r.json()), 201


@bp.delete("/admin/delete-user/<user_id>")
def admin_delete_user(user_id: str):
    if err := require_teacher_token():
        return err
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.delete(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=sb_headers(),
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return "", 204


@bp.post("/admin/reset-password")
def admin_reset_password():
    if err := require_teacher_token():
        return err
    body      = request.get_json(silent=True) or {}
    user_id   = body.get("user_id", "").strip()
    password  = body.get("password", "").strip()
    if not user_id or not password:
        from flask import abort
        abort(400)
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.put(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=sb_headers(),
        json={"password": password},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify({"ok": True})


@bp.post("/admin/set-teacher/<user_id>")
def admin_set_teacher(user_id: str):
    if err := require_teacher_token():
        return err
    if not is_owner_session():
        return jsonify({"error": "Apenas o owner pode promover professores"}), 403
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.put(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=sb_headers(),
        json={"user_metadata": {"role": "teacher"}},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify({"ok": True})


@bp.get("/admin/reports")
def admin_reports_list():
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("reports", {
            "select": "id,title,scope,scope_label,created_at,data",
            "order": "created_at.desc",
            "limit": "50",
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    # Retorna resumo sem o data completo (só contagem)
    result = []
    for r in rows:
        d = r.get("data") or {}
        students = d.get("students") or []
        result.append({
            "id":          r["id"],
            "title":       r["title"],
            "scope":       r["scope"],
            "scope_label": r["scope_label"],
            "created_at":  r["created_at"],
            "student_count": len(students),
            "summary":     d.get("summary") or {},
        })
    return jsonify({"reports": result})


@bp.get("/admin/reports/<report_id>")
def admin_report_detail(report_id: str):
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("reports", {"select": "*", "id": f"eq.{report_id}"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    if not rows:
        from flask import abort
        abort(404)
    return jsonify(rows[0])


@bp.post("/admin/reports/generate")
def admin_report_generate():
    if err := require_teacher_token():
        return err

    body        = request.get_json(silent=True) or {}
    scope       = body.get("scope", "all")        # all | teacher | student
    scope_ref   = body.get("scope_ref", "")       # teacher_id ou student_id
    scope_label = body.get("scope_label", "")     # nome legível
    start       = body.get("start", "").strip()
    end         = body.get("end",   "").strip()
    title       = body.get("title", "").strip()

    if not start or not end:
        return jsonify({"error": "Período obrigatório"}), 400

    supabase_url = current_app.config["SUPABASE_URL"]

    # Busca todos os usuários
    r_users = http.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        params={"per_page": 200},
        timeout=10,
    )
    if not r_users.ok:
        return jsonify({"error": "Erro ao buscar usuários"}), 500

    users_raw = r_users.json().get("users", [])
    # Monta mapa completo (inclui teacher_id para filtro)
    all_users = {
        u["id"]: {
            "email":      u.get("email", ""),
            "name":       (u.get("user_metadata") or {}).get("name") or "",
            "role":       (u.get("user_metadata") or {}).get("role") or "",
            "teacher_id": (u.get("user_metadata") or {}).get("teacher_id") or "",
        }
        for u in users_raw
    }

    # Filtra por escopo
    if scope == "teacher" and scope_ref:
        filtered_ids = {uid for uid, info in all_users.items()
                        if info["teacher_id"] == scope_ref and info["role"] not in ("teacher", "owner")}
    elif scope == "student" and scope_ref:
        filtered_ids = {scope_ref} if scope_ref in all_users else set()
    else:
        filtered_ids = {uid for uid, info in all_users.items()
                        if info["role"] not in ("teacher", "owner")}

    if not filtered_ids:
        return jsonify({"error": "Nenhum aluno encontrado para esse escopo"}), 400

    end_ts = f"{end}T23:59:59"
    try:
        r_study = http.get(f"{supabase_url}/rest/v1/study_days", headers=sb_headers(),
            params=[("select","user_id,day"),("day",f"gte.{start}"),("day",f"lte.{end}")], timeout=10)
        r_prog  = http.get(f"{supabase_url}/rest/v1/module_progress", headers=sb_headers(),
            params=[("select","user_id,module_slug,updated_at"),("completed","gt.0"),
                    ("updated_at",f"gte.{start}"),("updated_at",f"lte.{end_ts}")], timeout=10)
        r_quiz  = http.get(f"{supabase_url}/rest/v1/quiz_answers", headers=sb_headers(),
            params=[("select","user_id,question,correct"),
                    ("created_at",f"gte.{start}"),("created_at",f"lte.{end_ts}")], timeout=10)
        r_study.raise_for_status(); r_prog.raise_for_status(); r_quiz.raise_for_status()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    from collections import defaultdict, Counter
    study_map = defaultdict(list)
    prog_map  = defaultdict(list)
    quiz_map  = defaultdict(list)
    for row in r_study.json(): study_map[row["user_id"]].append(row["day"])
    for row in r_prog.json():  prog_map[row["user_id"]].append(row["module_slug"])
    for row in r_quiz.json():  quiz_map[row["user_id"]].append(row)

    # Mapa id → nome de professores para exibir
    teacher_name_map = {uid: info["name"] or info["email"].split("@")[0]
                        for uid, info in all_users.items()
                        if info["role"] in ("teacher", "owner")}

    students_data = []
    for uid in filtered_ids:
        info = all_users[uid]
        quiz_user  = quiz_map[uid]
        total_q    = len(quiz_user)
        correct_q  = sum(1 for q in quiz_user if q.get("correct"))
        wrong      = [q["question"] for q in quiz_user if not q.get("correct") and q.get("question")]
        top_errors = [{"question": q, "count": c} for q, c in Counter(wrong).most_common(5)]
        students_data.append({
            "id":                uid,
            "name":              info["name"] or info["email"].split("@")[0],
            "email":             info["email"],
            "teacher_id":        info["teacher_id"],
            "teacher_name":      teacher_name_map.get(info["teacher_id"], ""),
            "study_days":        len(study_map[uid]),
            "modules_completed": len(prog_map[uid]),
            "modules":           prog_map[uid],
            "quiz_total":        total_q,
            "quiz_correct":      correct_q,
            "quiz_accuracy":     round(correct_q / total_q * 100) if total_q > 0 else None,
            "top_errors":        top_errors,
        })

    students_data.sort(key=lambda x: x["study_days"], reverse=True)

    total_mods = sum(s["modules_completed"] for s in students_data)
    total_days = sum(s["study_days"] for s in students_data)
    acc_vals   = [s["quiz_accuracy"] for s in students_data if s["quiz_accuracy"] is not None]

    summary = {
        "total_students":    len(students_data),
        "avg_modules":       round(total_mods / len(students_data), 1) if students_data else 0,
        "avg_study_days":    round(total_days / len(students_data), 1) if students_data else 0,
        "avg_quiz_accuracy": round(sum(acc_vals) / len(acc_vals)) if acc_vals else None,
    }

    if not title:
        from datetime import datetime
        month_label = datetime.strptime(start, "%Y-%m-%d").strftime("%B/%Y").capitalize()
        scope_part  = f"– {scope_label}" if scope_label else ""
        title = f"Relatório {scope_part} {month_label}".strip()

    report_row = {
        "title":       title,
        "scope":       scope,
        "scope_ref":   scope_ref or None,
        "scope_label": scope_label or None,
        "created_by":  session.get("user_id"),
        "data": {
            "period":   {"start": start, "end": end},
            "students": students_data,
            "summary":  summary,
        },
    }

    try:
        saved = sb_post("reports", report_row)
        if isinstance(saved, list): saved = saved[0]
        return jsonify({"ok": True, "id": saved.get("id")}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
