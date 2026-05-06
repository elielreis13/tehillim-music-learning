import time

from flask import jsonify, make_response, redirect, render_template, request, session
import requests as http

from . import bp
from tehillim.extensions import sb_get


def _traduzir_erro(msg: str) -> str:
    if "Invalid login credentials" in msg: return "E-mail ou senha incorretos."
    if "Email not confirmed"        in msg: return "Confirme seu e-mail antes de entrar."
    if "rate limit"      in msg.lower(): return "Muitas tentativas. Aguarde alguns minutos."
    return "Algo deu errado. Tente novamente."


@bp.get("/login")
def login():
    return render_template("auth/login.html")


@bp.post("/auth/login")
def do_login():
    from flask import current_app
    data     = request.get_json(force=True, silent=True) or {}
    email    = (data.get("email") or "").strip()
    password = data.get("password") or ""

    # Modo dev
    if email == "dev" and password == "dev":
        session.permanent = True
        session["user_id"]      = "dev-user-00000000-0000-0000-0000-000000000000"
        session["email"]        = "dev@tehillim.dev"
        session["name"]         = "Dev"
        session["is_teacher"]   = True
        session["module_slugs"] = []
        session["access_token"] = "__dev__"
        session["expires_at"]   = int(time.time()) + 3600 * 24 * 7
        return jsonify({"ok": True})

    if not email or not password:
        return jsonify({"error": "E-mail e senha são obrigatórios."}), 400

    sb_url   = current_app.config["SUPABASE_URL"]
    anon_key = current_app.config["SUPABASE_ANON_KEY"]

    try:
        r = http.post(
            f"{sb_url}/auth/v1/token?grant_type=password",
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=10,
        )
    except http.exceptions.Timeout:
        return jsonify({"error": "Serviço indisponível. Tente novamente em instantes."}), 503
    except Exception:
        return jsonify({"error": "Sem conexão. Verifique sua internet."}), 503

    if not r.ok:
        err = r.json().get("error_description") or r.json().get("msg") or ""
        return jsonify({"error": _traduzir_erro(err)}), 401

    sb   = r.json()
    user = sb["user"]
    meta = user.get("user_metadata") or {}
    is_teacher = meta.get("role") == "teacher"

    module_slugs = []
    if not is_teacher:
        try:
            rows = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{user['id']}"})
            module_slugs = [row["module_slug"] for row in rows]
        except Exception:
            pass

    session.permanent       = True
    session["user_id"]      = user["id"]
    session["email"]        = user["email"]
    session["name"]         = meta.get("name") or user["email"].split("@")[0]
    session["is_teacher"]   = is_teacher
    session["module_slugs"] = module_slugs
    session["access_token"] = sb["access_token"]
    session["refresh_token"]= sb.get("refresh_token", "")
    session["expires_at"]   = sb.get("expires_at", int(time.time()) + 3600)

    return jsonify({"ok": True})


@bp.get("/logout")
def logout():
    session.clear()
    resp = make_response(redirect("/landing"))
    resp.delete_cookie("ta")
    return resp
