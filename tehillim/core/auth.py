import requests
from flask import current_app, jsonify, redirect, session as flask_session

from .supabase import sb_headers, sb_get


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
