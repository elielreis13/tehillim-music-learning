import requests
from flask import current_app


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