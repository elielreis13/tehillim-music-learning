import json
from urllib.parse import unquote

import requests
from flask import current_app, jsonify, redirect, request


def sb_headers():
    """Cabeçalhos com a service key para chamadas administrativas ao Supabase."""
    key = current_app.config["SUPABASE_SERVICE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def sb_get(table: str, params: dict | None = None) -> list:
    """Faz GET na API REST do Supabase e retorna a lista de registros."""
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.get(url, headers=sb_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_post(table: str, payload, prefer: str = "return=representation"):
    """Faz POST (inserção) na API REST do Supabase."""
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.post(url, headers={**sb_headers(), "Prefer": prefer}, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_put(path: str, payload: dict):
    """Faz PUT na API de administração do Supabase Auth."""
    url = f"{current_app.config['SUPABASE_URL']}{path}"
    r = requests.put(url, headers=sb_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_delete(table: str, params: dict):
    """Faz DELETE na API REST do Supabase."""
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.delete(url, headers=sb_headers(), params=params, timeout=10)
    r.raise_for_status()


def get_user_from_token(token: str) -> dict | None:
    """Valida um Bearer token e retorna os dados do usuário, ou None se inválido."""
    url = f"{current_app.config['SUPABASE_URL']}/auth/v1/user"
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "apikey": current_app.config["SUPABASE_ANON_KEY"]},
        timeout=5,
    )
    return r.json() if r.ok else None


def is_teacher_request() -> bool:
    """Retorna True se o cookie 'ta' indica que o usuário é professor."""
    try:
        raw  = request.cookies.get("ta", "")
        data = json.loads(unquote(raw)) if raw else {}
        return bool(data.get("t", False))
    except Exception:
        return False


def require_teacher():
    """Redireciona para '/' se o usuário não for professor. Uso: if err := require_teacher(): return err"""
    if not is_teacher_request():
        return redirect("/")
    return None


def require_teacher_token():
    """Versão para APIs: valida Bearer token e verifica papel de professor. Retorna 403 ou None."""
    auth_header = request.headers.get("Authorization", "")

    # Modo dev: token especial é aceito como professor
    if auth_header == "Bearer __dev__":
        return None

    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Não autorizado"}), 403

    user_data = get_user_from_token(auth_header[7:])
    if not user_data:
        return jsonify({"error": "Token inválido"}), 403

    is_teacher = (user_data.get("user_metadata") or {}).get("role") == "teacher"
    if not is_teacher:
        return jsonify({"error": "Acesso restrito ao professor"}), 403

    return None