from __future__ import annotations

from flask import current_app, jsonify, request, session

from . import bp
from tehillim.extensions import sb_get, sb_headers, sb_post, require_teacher_token
import requests as http


@bp.post("/recordings/upload")
def recordings_upload():
    """Student uploads a practice recording. Saves to Supabase Storage + submissions table."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login necessário"}), 401

    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    module_slug = request.form.get("module_slug", "").strip()
    if not module_slug:
        return jsonify({"error": "module_slug obrigatório"}), 400

    bpm_raw = request.form.get("bpm", "").strip()
    bpm_tag = f"bpm{bpm_raw}_" if bpm_raw.isdigit() else ""

    allowed = {"audio/webm", "audio/ogg", "audio/mpeg", "audio/mp4", "audio/wav", "audio/x-wav"}
    content_type = f.content_type or "audio/webm"
    if content_type not in allowed and not content_type.startswith("audio/"):
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400

    import uuid
    ext = "webm" if "webm" in content_type else "ogg" if "ogg" in content_type else "mp3"
    filename = f"recordings/{user_id}/{module_slug}/{bpm_tag}{uuid.uuid4().hex}.{ext}"

    supabase_url = current_app.config["SUPABASE_URL"]
    service_key  = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket = "recordings"

    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
    headers = {
        "apikey":        service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type":  content_type,
        "x-upsert":      "false",
    }
    r = http.post(upload_url, headers=headers, data=f.read(), timeout=60)
    if not r.ok:
        return jsonify({"error": f"Storage: {r.status_code} {r.text}"}), 500

    audio_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"

    # Save record in submissions table (non-fatal)
    try:
        sb_post("submissions", {
            "user_id":     user_id,
            "module_slug": module_slug,
            "audio_url":   audio_url,
        })
    except Exception:
        pass

    return jsonify({"url": audio_url}), 200


@bp.get("/recordings/<module_slug>")
def recordings_list(module_slug: str):
    """Professor lists all recordings for a module."""
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("submissions", {
            "select": "id,user_id,module_slug,audio_url,created_at,professor_note",
            "module_slug": f"eq.{module_slug}",
            "order": "created_at.desc",
        })
        return jsonify(rows), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
