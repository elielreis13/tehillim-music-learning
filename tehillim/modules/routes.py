from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote, unquote

from flask import abort, redirect, render_template, request

from . import bp
from tehillim.content import get_group, get_module


def _ta_cookie() -> tuple[set, bool]:
    try:
        raw  = request.cookies.get("ta", "")
        data = json.loads(unquote(raw)) if raw else {}
        return set(data.get("s", [])), bool(data.get("t", False))
    except Exception:
        return set(), False


@bp.before_request
def require_login_for_app_pages():
    if request.endpoint == "modules.landing":
        return None
    if request.cookies.get("ta"):
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


@bp.get("/grupos")
def grupos_page():
    return render_template("pages/grupos.html", active_page="grupos")


@bp.get("/grupos/<group_slug>")
def group_page(group_slug: str):
    selected_group = get_group(group_slug)
    if selected_group is None:
        abort(404)
    granted_slugs, is_teacher_cookie = _ta_cookie()
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
    granted_slugs, is_teacher_cookie = _ta_cookie()
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
