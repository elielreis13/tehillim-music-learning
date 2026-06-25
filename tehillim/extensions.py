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
    if not r.ok:
        raise requests.HTTPError(f"{r.status_code} {r.reason}: {r.text}", response=r)
    return r.json()


def sb_put(path: str, payload: dict):
    url = f"{current_app.config['SUPABASE_URL']}{path}"
    r = requests.put(url, headers=sb_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_patch(table: str, params: dict, payload: dict):
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.patch(url, headers={**sb_headers(), "Prefer": "return=representation"},
                       params=params, json=payload, timeout=10)
    if not r.ok:
        raise requests.HTTPError(f"{r.status_code} {r.reason}: {r.text}", response=r)
    return r.json()


def sb_upsert(table: str, payload, conflict_col: str = "id"):
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}?on_conflict={conflict_col}"
    r = requests.post(
        url,
        headers={**sb_headers(), "Prefer": "resolution=merge-duplicates,return=representation"},
        json=payload,
        timeout=10,
    )
    if not r.ok:
        raise requests.HTTPError(f"{r.status_code} {r.reason}: {r.text}", response=r)
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


def is_owner_session() -> bool:
    """True somente para o owner da plataforma (vê todos os alunos)."""
    return flask_session.get("is_owner", False)


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


def get_student_teacher_id(student_user_id: str) -> str | None:
    """Busca o teacher_id dos metadados do aluno. Retorna None em caso de erro."""
    try:
        supabase_url = current_app.config["SUPABASE_URL"]
        r = requests.get(
            f"{supabase_url}/auth/v1/admin/users/{student_user_id}",
            headers=sb_headers(),
            timeout=6,
        )
        if not r.ok:
            return None
        return (r.json().get("user_metadata") or {}).get("teacher_id")
    except Exception:
        return None


def assert_student_owner(student_user_id: str):
    """Retorna (None, None) se autorizado, ou (response, status) se não."""
    # Busca metadados do alvo para verificar proteções
    try:
        supabase_url = current_app.config["SUPABASE_URL"]
        r = requests.get(
            f"{supabase_url}/auth/v1/admin/users/{student_user_id}",
            headers=sb_headers(),
            timeout=6,
        )
        if r.ok:
            target_meta = (r.json().get("user_metadata") or {})
            if target_meta.get("role") == "owner":
                return jsonify({"error": "A conta owner não pode ser modificada"}), 403
            teacher_id = target_meta.get("teacher_id")
        else:
            teacher_id = None
    except Exception:
        teacher_id = None

    if is_owner_session():
        return None, None
    if teacher_id == flask_session.get("user_id"):
        return None, None
    return jsonify({"error": "Acesso negado"}), 403


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
