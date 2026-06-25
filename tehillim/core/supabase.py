import jwt
import requests
from flask import current_app

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
