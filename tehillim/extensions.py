import jwt
import requests
from flask import current_app, jsonify, redirect, session as flask_session

_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        url = f"{current_app.config['SUPABASE_URL']}/auth/v1/.well-known/jwks.json"
        _jwks_client = jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=3600)
    return _jwks_client


def sb_headers():
    key = current_app.config["SUPABASE_SERVICE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def sb_get(table: str, params: dict | None = None) -> list:
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.get(url, headers=sb_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_post(table: str, payload, prefer: str = "return=representation"):
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.post(url, headers={**sb_headers(), "Prefer": prefer}, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_put(path: str, payload: dict):
    url = f"{current_app.config['SUPABASE_URL']}{path}"
    r = requests.put(url, headers=sb_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_delete(table: str, params: dict):
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.delete(url, headers=sb_headers(), params=params, timeout=10)
    r.raise_for_status()


def get_current_user() -> dict | None:
    """Retorna o usuário da sessão Flask, ou None se não autenticado."""
    user_id = flask_session.get("user_id")
    if not user_id:
        return None
    return {
        "id":            user_id,
        "email":         flask_session.get("email", ""),
        "user_metadata": {
            "name": flask_session.get("name", ""),
            "role": "teacher" if flask_session.get("is_teacher") else "aluno",
        },
    }


def is_teacher_session() -> bool:
    return flask_session.get("is_teacher", False)


def require_teacher():
    """Para rotas de página: redireciona se não for professor."""
    if not is_teacher_session():
        return redirect("/")
    return None


def require_teacher_token():
    """Para APIs: retorna 403 se não for professor, None se ok."""
    if is_teacher_session():
        return None
    return jsonify({"error": "Acesso restrito ao professor"}), 403


# Mantido para compatibilidade — valida JWT via JWKS (usado apenas se necessário)
def get_user_from_token(token: str) -> dict | None:
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "HS256"],
            audience="authenticated",
        )
        return {
            "id":            payload.get("sub"),
            "email":         payload.get("email", ""),
            "user_metadata": payload.get("user_metadata", {}),
        }
    except Exception:
        return None
