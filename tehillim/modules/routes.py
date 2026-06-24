from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from flask import abort, redirect, render_template, request, session

from . import bp
from tehillim.content import get_group, get_module
from tehillim.content.types import Exercise
from tehillim.content.helpers import module as make_module
from tehillim.extensions import sb_get


def _get_module_or_db(slug: str):
    """Return StudyModule from static files, falling back to DB."""
    m = get_module(slug)
    if m is not None:
        return m
    try:
        rows = sb_get("modules", {"select": "*", "slug": f"eq.{slug}"})
        if not rows:
            return None
        row = rows[0]
        exercises = tuple(
            Exercise(
                kind=e.get("kind", "exercise-mc"),
                prompt=e.get("prompt", ""),
                options=tuple(e.get("options") or []),
                answer=e.get("answer", ""),
            )
            for e in (row.get("exercises") or [])
        )
        return make_module(
            number=int(row.get("number") or 0),
            slug=row["slug"],
            title=row.get("title", ""),
            description=row.get("description", ""),
            topics=tuple(t.strip() for t in (row.get("topics") or "").split(",") if t.strip()),
            theory=row.get("theory", ""),
            visual=row.get("visual", ""),
            exercises=exercises,
            game=row.get("game", ""),
            game_kind=row.get("game_kind", "game-challenge"),
            video_url=row.get("video_url", ""),
        )
    except Exception:
        return None


def _get_access() -> tuple[set, bool]:
    is_teacher = session.get("is_teacher", False)
    user_id    = session.get("user_id")
    if not user_id or is_teacher:
        return set(), is_teacher
    try:
        rows  = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{user_id}"})
        slugs = {r["module_slug"] for r in rows}
        session["module_slugs"] = list(slugs)
        return slugs, False
    except Exception:
        return set(session.get("module_slugs", [])), False


@bp.before_request
def require_login_for_app_pages():
    if request.endpoint == "modules.landing":
        return None
    if session.get("user_id"):
        return None
    next_url = request.full_path.rstrip("?")
    return redirect(f"/login?next={quote(next_url)}")


@bp.get("/")
@bp.get("/landing")
def landing():
    return render_template("landing.html")


@bp.get("/inicio")
@bp.get("/index.html")
def index():
    return render_template("pages/home.html", active_page="inicio")


@bp.get("/grupos/<group_slug>")
def group_page(group_slug: str):
    selected_group = get_group(group_slug)
    if selected_group is None:
        abort(404)

    # Start with static modules for this group
    static_by_slug = {m.slug: m.to_summary() for m in selected_group.modules}

    # Merge in any DB modules that belong to this group
    try:
        db_rows = sb_get("modules", {
            "select": "slug,number,title,description,topics",
            "group_slug": f"eq.{group_slug}",
            "order": "number.asc",
        })
    except Exception:
        db_rows = []

    merged = dict(static_by_slug)
    for row in db_rows:
        topics_raw = row.get("topics") or ""
        topics = [t.strip() for t in topics_raw.split(",") if t.strip()]
        merged[row["slug"]] = {
            "number":      int(row.get("number") or 0),
            "slug":        row["slug"],
            "title":       row.get("title", ""),
            "description": row.get("description", ""),
            "topics":      topics,
            "step_count":  merged.get(row["slug"], {}).get("step_count", 0),
        }

    # Sort by global number (used only for ordering), position within list = local number
    modules_list = sorted(merged.values(), key=lambda m: (m.get("number", 0), m["slug"]))

    granted_slugs, is_teacher_cookie = _get_access()
    return render_template(
        "pages/group.html",
        group=selected_group,
        modules_list=modules_list,
        granted_slugs=granted_slugs,
        is_teacher_cookie=is_teacher_cookie,
        active_page="grupos",
    )


@bp.get("/trilhas")
def trilhas_page():
    return render_template("pages/trilhas.html", active_page="trilhas")


@bp.get("/revisoes")
def revisoes_page():
    return render_template("pages/revisoes.html", active_page="revisoes")


@bp.get("/exercicios")
def exercicios_page():
    return render_template("pages/exercicios.html", active_page="exercicios")


@bp.get("/aulas")
def aulas_page():
    return render_template("pages/aulas.html", active_page="aulas")


@bp.get("/desempenho")
def desempenho_page():
    return render_template("pages/desempenho.html", active_page="desempenho")


@bp.get("/conquistas")
def conquistas_page():
    return render_template("pages/desempenho.html", active_page="desempenho")


@bp.get("/mensagens")
def mensagens_page():
    return render_template("pages/mensagens.html", active_page="mensagens")


@bp.get("/notificacoes")
def notificacoes_page():
    return render_template("pages/notificacoes.html", active_page="notificacoes")


@bp.get("/configuracoes")
def configuracoes_page():
    from flask import redirect
    return redirect("/perfil")


@bp.get("/perfil")
def perfil_page():
    return render_template("pages/perfil.html", active_page="perfil")


_BONA_SHEETS    = Path(__file__).resolve().parent.parent / "static" / "bona"
_POZZOLI_SHEETS = Path(__file__).resolve().parent.parent / "static" / "pozzoli"


@bp.get("/modulos/<module_slug>")
def module_page(module_slug: str):
    selected_module = _get_module_or_db(module_slug)
    if selected_module is None:
        return redirect("/trilhas")
    granted_slugs, is_teacher_cookie = _get_access()
    access_ok = is_teacher_cookie or module_slug in granted_slugs
    if 101 <= selected_module.number <= 140:
        has_sheet = (_BONA_SHEETS / f"{module_slug}.musicxml").exists()
        return render_template(
            "pages/bona_module.html",
            module=selected_module,
            access_ok=access_ok,
            has_sheet=has_sheet,
        )
    if (201 <= selected_module.number <= 212) or (301 <= selected_module.number <= 400):
        has_sheet = (_POZZOLI_SHEETS / f"{module_slug}.musicxml").exists()
        return render_template(
            "pages/pozzoli_module.html",
            module=selected_module,
            access_ok=access_ok,
            has_sheet=has_sheet,
        )
    return render_template(
        "pages/module.html",
        module=selected_module,
        access_ok=access_ok,
    )


@bp.get("/jogos")
def jogos_page():
    return render_template("pages/jogos.html", active_page="jogos")


@bp.get("/demo/vozes")
def vozes_demo():
    if err := require_login_for_app_pages():
        return err
    return render_template("pages/vozes_demo.html")


@bp.get("/bona-player/<slug>")
def bona_player(slug: str):
    has_sheet = (_BONA_SHEETS / f"{slug}.musicxml").exists()
    return render_template("pages/bona_player.html", slug=slug, has_sheet=has_sheet)


@bp.get("/pozzoli-player/<slug>")
def pozzoli_player(slug: str):
    has_sheet = (_POZZOLI_SHEETS / f"{slug}.musicxml").exists()
    # Formata slug "pozzoli-p1" → "Pozzoli P1"
    module_title = slug.replace("-", " ").title()
    return render_template("pages/pozzoli_player.html", slug=slug, has_sheet=has_sheet, module_title=module_title)
