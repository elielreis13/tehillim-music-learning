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
    return render_template("pages/admin.html")
