from flask import make_response, redirect, render_template

from . import bp


@bp.get("/login")
def login():
    return render_template("auth/login.html")


@bp.get("/logout")
def logout():
    resp = make_response(redirect("/landing"))
    resp.delete_cookie("ta")
    return resp

