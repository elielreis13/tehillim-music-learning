from flask import render_template
from . import bp

@bp.get("/")
def landing():
    return render_template("landing.html")