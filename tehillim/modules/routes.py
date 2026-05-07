from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from flask import abort, redirect, render_template, request, session

from . import bp
from tehillim.content import get_group, get_module
from tehillim.extensions import sb_get


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
    granted_slugs, is_teacher_cookie = _get_access()
    return render_template(
        "pages/group.html",
        group=selected_group,
        granted_slugs=granted_slugs,
        is_teacher_cookie=is_teacher_cookie,
        active_page="grupos",
    )


@bp.get("/trilhas")
def trilhas_page():
    return render_template("pages/trilhas.html", active_page="trilhas")


@bp.get("/aulas")
def aulas_page():
    return render_template("pages/aulas.html", active_page="aulas")


@bp.get("/desempenho")
def desempenho_page():
    return render_template("pages/desempenho.html", active_page="desempenho")


@bp.get("/conquistas")
def conquistas_page():
    return render_template("pages/conquistas.html", active_page="conquistas")


@bp.get("/notificacoes")
def notificacoes_page():
    return render_template("pages/notificacoes.html", active_page="notificacoes")


@bp.get("/configuracoes")
def configuracoes_page():
    return render_template("pages/configuracoes.html", active_page="configuracoes")


@bp.get("/perfil")
def perfil_page():
    return render_template("pages/perfil.html", active_page="perfil")


_BONA_SHEETS = Path(__file__).resolve().parent.parent / "static" / "bona"


@bp.get("/modulos/<module_slug>")
def module_page(module_slug: str):
    selected_module = get_module(module_slug)
    if selected_module is None:
        abort(404)
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
    return render_template(
        "pages/module.html",
        module=selected_module,
        access_ok=access_ok,
    )


@bp.get("/jogos")
def jogos_page():
    return render_template("pages/jogos.html", active_page="jogos")


@bp.get("/bona-player/<slug>")
def bona_player(slug: str):
    has_sheet = (_BONA_SHEETS / f"{slug}.musicxml").exists()
    return render_template("pages/bona_player.html", slug=slug, has_sheet=has_sheet)
