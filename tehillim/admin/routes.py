from flask import render_template

from . import bp
from tehillim.extensions import require_teacher


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
