from flask import render_template, abort
import requests as http

from . import bp
from tehillim.extensions import require_teacher, sb_headers
from flask import current_app


@bp.get("/dashboard")
def dashboard():
    if err := require_teacher():
        return err
    return render_template("pages/dashboard.html")


@bp.get("/admin")
def admin():
    if err := require_teacher():
        return err
    return render_template("pages/professor_admin.html", active_page="admin")


@bp.get("/professor/alunos")
def professor_alunos():
    if err := require_teacher():
        return err
    return render_template("pages/professor_alunos.html", active_page="professor_alunos")


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
    return render_template(
        "pages/professor_aluno_detalhe.html",
        student=student,
        active_page="professor_alunos",
    )
