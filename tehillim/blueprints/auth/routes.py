import time

from flask import jsonify, make_response, redirect, render_template, request, session
import requests as http

from . import bp
from tehillim.extensions import sb_get


def _traduzir_erro(msg: str) -> str:
    if "Invalid login credentials" in msg: return "Usuário ou senha incorretos."
    if "Email not confirmed"        in msg: return "Confirme seu e-mail antes de entrar."
    if "rate limit"      in msg.lower(): return "Muitas tentativas. Aguarde alguns minutos."
    return "Algo deu errado. Tente novamente."


def _email_by_username(username: str, sb_url: str, sb_headers: dict) -> str | None:
    """Busca o e-mail de um usuário pelo nome cadastrado em user_metadata."""
    try:
        r = http.get(f"{sb_url}/auth/v1/admin/users",
                     headers=sb_headers, params={"per_page": 1000}, timeout=10)
        if not r.ok:
            return None
        name_lower = username.lower()
        for u in r.json().get("users", []):
            meta = u.get("user_metadata") or {}
            if (meta.get("name") or "").lower() == name_lower:
                return u["email"]
    except Exception:
        pass
    return None


@bp.get("/login")
def login():
    return render_template("auth/login.html")


@bp.post("/auth/login")
def do_login():
    from flask import current_app
    from tehillim.extensions import sb_headers as _sb_headers
    data     = request.get_json(force=True, silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if not username or not password:
        return jsonify({"error": "Nome de usuário e senha são obrigatórios."}), 400

    sb_url   = current_app.config["SUPABASE_URL"]
    anon_key = current_app.config["SUPABASE_ANON_KEY"]

    email = _email_by_username(username, sb_url, _sb_headers())
    if not email:
        return jsonify({"error": "Usuário não encontrado."}), 401

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
    is_owner   = meta.get("role") == "owner"
    is_teacher = meta.get("role") in ("teacher", "owner")

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
    session["avatar"]       = meta.get("avatar") or ""
    session["avatar_url"]   = meta.get("avatar_url") or ""
    session["is_teacher"]   = is_teacher
    session["is_owner"]     = is_owner
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
