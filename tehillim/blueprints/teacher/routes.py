from flask import render_template, abort
import requests as http

from . import bp
from tehillim.extensions import require_teacher, sb_headers, sb_get
from tehillim.content import module_summaries
from flask import current_app


@bp.get("/dashboard")
def dashboard():
    if err := require_teacher():
        return err
    return render_template("teacher/dashboard.html")


@bp.get("/admin")
def admin():
    if err := require_teacher():
        return err
    return render_template("teacher/admin.html", active_page="admin")


@bp.get("/professor/alunos")
def professor_alunos():
    if err := require_teacher():
        return err
    from tehillim.content import groups_summary
    return render_template(
        "teacher/alunos.html",
        active_page="professor_alunos",
        groups=groups_summary(),
    )


@bp.get("/professor/alunos/<user_id>")
def professor_aluno_detalhe(user_id: str):
    if err := require_teacher():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.get(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=sb_headers(),
        timeout=10,
    )
    if not r.ok:
        abort(404)
    u = r.json()
    student = {
        "id":    u["id"],
        "email": u.get("email", ""),
        "name":  (u.get("user_metadata") or {}).get("name") or "",
    }
    from tehillim.content import groups_summary
    return render_template(
        "teacher/aluno_detalhe.html",
        student=student,
        groups=groups_summary(),
        active_page="admin",
    )


@bp.get("/admin/relatorios")
def professor_relatorios():
    if err := require_teacher():
        return err
    return render_template("teacher/relatorios.html", active_page="admin")


@bp.get("/professor/mensagens")
def professor_mensagens():
    if err := require_teacher():
        return err
    return render_template("teacher/mensagens.html", active_page="professor_mensagens")


@bp.get("/admin/exercicios")
def professor_exercicios():
    if err := require_teacher():
        return err
    students = _fetch_students()
    return render_template("teacher/exercicios.html", active_page="admin", students=students)


@bp.get("/admin/desafios")
def professor_desafios():
    if err := require_teacher():
        return err
    from tehillim.content import groups_summary
    return render_template("teacher/desafios.html", active_page="admin", groups=groups_summary())


@bp.get("/admin/jogos")
def professor_jogos():
    if err := require_teacher():
        return err
    modules = module_summaries()
    return render_template(
        "teacher/jogos.html",
        active_page="professor_jogos",
        modules=modules,
    )


@bp.get("/admin/jogos/lista")
def professor_jogos_lista():
    if err := require_teacher():
        return err
    try:
        games = sb_get("module_games", {"select": "*", "order": "module_slug.asc,order_index.asc"})
    except Exception:
        games = []
    return render_template(
        "teacher/jogos_lista.html",
        active_page="professor_jogos",
        games=games,
    )


# ── Módulos ───────────────────────────────────────────────────────────────────

@bp.get("/admin/modulos")
def professor_modulos():
    if err := require_teacher():
        return err
    from tehillim.content.groups import GROUPS
    static_mods = module_summaries()
    group_by_slug = {}
    for g in GROUPS:
        for m in g.modules:
            group_by_slug[m.slug] = g.name
    try:
        db_rows = sb_get("modules", {
            "select": "slug,number,title,game_kind,group_slug,updated_at",
            "order": "number.asc",
        })
        db_slugs = {r["slug"] for r in db_rows}
        static_slugs = {m["slug"] for m in static_mods}
        db_only_mods = [r for r in db_rows if r["slug"] not in static_slugs]
    except Exception:
        db_rows = []
        db_slugs = set()
        db_only_mods = []
    return render_template(
        "teacher/modulos.html",
        active_page="professor_modulos",
        static_mods=static_mods,
        db_slugs=list(db_slugs),
        group_by_slug=group_by_slug,
        db_only_mods=db_only_mods,
    )


@bp.get("/admin/modulos/novo")
def professor_modulos_novo():
    if err := require_teacher():
        return err
    next_number = None
    try:
        rows = sb_get("modules", {"select": "number", "order": "number.desc", "limit": "1"})
        if rows:
            next_number = (rows[0].get("number") or 0) + 1
        else:
            next_number = 1
    except Exception:
        pass
    return _modulos_editor_page(module_data=None, mode="new", next_number=next_number)


@bp.get("/admin/modulos/<slug>/editar")
def professor_modulos_editar(slug: str):
    if err := require_teacher():
        return err
    # DB first
    try:
        rows = sb_get("modules", {"select": "*", "slug": f"eq.{slug}"})
        if rows:
            return _modulos_editor_page(module_data=rows[0], mode="edit", source="db")
    except Exception:
        pass
    # Fall back to .md
    from tehillim.content import get_module
    m = get_module(slug)
    if m is None:
        abort(404)
    module_data = _studymodule_to_dict(m)
    return _modulos_editor_page(module_data=module_data, mode="edit", source="md")


def _modulos_editor_page(module_data, mode, source="db", next_number=None):
    from tehillim.content.groups import GROUPS
    from tehillim.content.helpers import STEP_KINDS
    available_groups = [{"slug": g.slug, "name": g.name} for g in GROUPS]
    game_kinds = [k for k in STEP_KINDS if k.startswith("game-")]
    students = _fetch_students()
    return render_template(
        "teacher/modulos_editor.html",
        active_page="professor_modulos",
        module_data=module_data,
        available_groups=available_groups,
        game_kinds=game_kinds,
        mode=mode,
        source=source,
        next_number=next_number,
        students=students,
    )


def _fetch_students() -> list[dict]:
    """Return [{email, name}] for all auth users, best-effort."""
    try:
        supabase_url = current_app.config["SUPABASE_URL"]
        r = http.get(
            f"{supabase_url}/auth/v1/admin/users",
            headers=sb_headers(),
            params={"per_page": 200},
            timeout=8,
        )
        if not r.ok:
            return []
        users_raw = r.json().get("users", [])
        result = []
        for u in users_raw:
            email = u.get("email", "")
            name = (u.get("user_metadata") or {}).get("name") or ""
            if email:
                result.append({"email": email, "name": name or email})
        result.sort(key=lambda s: s["name"].lower())
        return result
    except Exception:
        return []


def _studymodule_to_dict(m) -> dict:
    """Convert a StudyModule (from .md) into an editable dict for the editor form."""
    theory = visual = game = ""
    game_kind = "game-challenge"
    exercises = []

    for step in m.steps:
        kind = step.kind
        body = step.body

        if kind == "theory":
            cut = "\n\nComo praticar:"
            theory = body[:body.index(cut)] if cut in body else body

        elif kind == "visual":
            cut = "\n\nObserve o desenho"
            visual = body[:body.index(cut)] if cut in body else body

        elif kind.startswith("game-"):
            game_kind = kind
            cut = "\n\nObjetivo: fixar"
            game = body[:body.index(cut)] if cut in body else body

        elif kind.startswith("exercise-"):
            exercises.append({
                "kind":    kind,
                "prompt":  step.prompt,
                "options": list(step.options),
                "answer":  step.answer,
            })

    return {
        "number":      m.number,
        "slug":        m.slug,
        "title":       m.title,
        "description": m.description,
        "topics":      ", ".join(m.topics),
        "group_slug":  "",
        "video_url":   "" if m.video_url == "video_placeholder_url" else (m.video_url or ""),
        "theory":           theory,
        "theory_audio_url": "",
        "visual":           visual,
        "exercises":        exercises,
        "game":             game,
        "game_kind":        game_kind,
        "game_data":        {},
    }
