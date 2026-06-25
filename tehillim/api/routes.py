from __future__ import annotations

from flask import abort, current_app, jsonify, request, session
import requests as http

from . import bp
from tehillim.content import (
    get_module, groups_summary, modules_payload,
    get_student_extra_lessons, add_student_extra_lesson, delete_student_extra_lesson,
)
from tehillim.content.demo_games import DEMO_GAMES
from tehillim.extensions import (
    sb_delete, sb_get, sb_headers, sb_post, sb_put, sb_upsert, sb_patch,
    require_teacher_token, is_owner_session, assert_student_owner,
    get_student_teacher_id,
)


# ── Jogos ─────────────────────────────────────────────────────────────────────

@bp.get("/games/demo")
def games_demo():
    return jsonify({"games": DEMO_GAMES})


# ── Conteúdo público ──────────────────────────────────────────────────────────

@bp.get("/groups")
def group_list():
    from tehillim.content.groups import GROUPS
    groups = [g.to_summary() for g in GROUPS]
    try:
        db_rows = sb_get("modules", {
            "select": "number,slug,title,description,topics,group_slug",
            "order": "number.asc",
        })
        static_slugs = {m["slug"] for g in groups for m in g["modules"]}
        group_by_slug = {g["slug"]: g for g in groups}
        for row in db_rows:
            if row["slug"] in static_slugs:
                continue
            gs = (row.get("group_slug") or "").strip()
            if not gs or gs not in group_by_slug:
                continue
            g = group_by_slug[gs]
            topics_raw = row.get("topics") or ""
            g["modules"].append({
                "number": row.get("number") or 0,
                "slug": row["slug"],
                "title": row["title"],
                "description": row.get("description") or "",
                "topics": [t.strip() for t in topics_raw.split(",") if t.strip()] if topics_raw else [],
                "step_count": 3,
                "video_url": "",
            })
            g["modules"].sort(key=lambda m: m.get("number") or 0)
            g["module_count"] = len(g["modules"])
    except Exception:
        pass
    return jsonify({"groups": groups})


@bp.get("/modules")
def modules():
    return jsonify({"modules": modules_payload()})


def _db_row_to_payload(row: dict) -> dict:
    """Build a full module payload from a DB modules row."""
    from tehillim.content.types import Exercise
    from tehillim.content.helpers import module as make_module
    exercises = tuple(
        Exercise(kind=e.get("kind", "exercise-mc"), prompt=e.get("prompt", ""),
                 options=tuple(e.get("options") or []), answer=e.get("answer", ""))
        for e in (row.get("exercises") or [])
    )
    m = make_module(
        number=int(row.get("number") or 0),
        slug=row["slug"],
        title=row["title"],
        description=row.get("description", ""),
        topics=tuple(t.strip() for t in (row.get("topics") or "").split(",") if t.strip()),
        theory=row.get("theory", ""),
        visual=row.get("visual", ""),
        exercises=exercises,
        game=row.get("game", ""),
        game_kind=row.get("game_kind", "game-challenge"),
        video_url=row.get("video_url", ""),
    )
    payload = m.to_payload()
    payload["group_slug"] = row.get("group_slug", "")
    # Inject theory_audio_url into the theory step
    theory_audio = row.get("theory_audio_url", "")
    if theory_audio:
        for step in payload["steps"]:
            if step["kind"] == "theory":
                step["theory_audio_url"] = theory_audio
                break
    # Inject game_data into the final game step if stored on the module row
    gd = row.get("game_data") or {}
    if gd and payload["steps"]:
        last = payload["steps"][-1]
        if last["kind"].startswith("game-"):
            last["game_data"] = gd
    return payload


@bp.get("/modules/<module_slug>")
def module_content(module_slug: str):
    # DB takes priority over .md
    payload = None
    try:
        rows = sb_get("modules", {"select": "*", "slug": f"eq.{module_slug}"})
        if rows:
            payload = _db_row_to_payload(rows[0])
    except Exception:
        pass
    if payload is None:
        selected_module = get_module(module_slug)
        if selected_module is None:
            abort(404)
        payload = selected_module.to_payload()
    try:
        db_games = sb_get("module_games", {
            "select": "*",
            "module_slug": f"eq.{module_slug}",
            "order": "order_index.asc",
        })
    except Exception:
        db_games = []
    for g in db_games:
        payload["steps"].append({
            "slug":      f"{module_slug}-game-{g['id'][:8]}",
            "title":     g["title"],
            "kind":      g["game_kind"],
            "summary":   g.get("description", ""),
            "body":      g.get("body", ""),
            "prompt":    "Conclua a missão e marque esta etapa como feita.",
            "options":   [],
            "answer":    "",
            "vf_data":   None,
            "game_data": g.get("game_data") or {},
        })
    payload["step_count"] = len(payload["steps"])
    return jsonify(payload)


@bp.post("/admin/jogos")
def admin_jogos_create():
    if err := require_teacher_token():
        return err
    data = request.get_json(silent=True) or {}
    required = ("module_slug", "title", "game_kind")
    if any(f not in data or not data[f] for f in required):
        return jsonify({"error": "Preencha: módulo, título e tipo de jogo."}), 400
    import json as _json, re as _re
    _UUID_RE = _re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.I)
    def _safe_uuid(v):
        return v if (v and _UUID_RE.match(str(v))) else None
    try:
        existing = sb_get("module_games", {
            "select": "order_index",
            "module_slug": f"eq.{data['module_slug']}",
            "order": "order_index.desc",
            "limit": "1",
        })
        next_index = (existing[0]["order_index"] + 1) if existing else 0
        game_data = data.get("game_data", {})
        payload = {
            "module_slug":  data["module_slug"],
            "title":        data["title"],
            "description":  data.get("description", ""),
            "game_kind":    data["game_kind"],
            "body":         data.get("body", ""),
            "game_data":    game_data,
            "order_index":  next_index,
            "created_by":   _safe_uuid(session.get("user_id")),
        }
        try:
            row = sb_post("module_games", payload)
        except Exception as first_exc:
            # game_data column may not exist yet — retry without it
            if "game_data" in str(first_exc):
                payload.pop("game_data")
                payload["body"] = _json.dumps(game_data, ensure_ascii=False)
                row = sb_post("module_games", payload)
            else:
                raise
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    created = row[0] if isinstance(row, list) else row
    return jsonify({"game": created}), 201


@bp.delete("/admin/jogos/<game_id>")
def admin_jogos_delete(game_id: str):
    if err := require_teacher_token():
        return err
    try:
        sb_delete("module_games", {"id": f"eq.{game_id}"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    return jsonify({"ok": True})


@bp.post("/admin/modulos")
def admin_modulos_save():
    """Upsert a module into the DB (create or overwrite by slug)."""
    if err := require_teacher_token():
        return err
    data = request.get_json(silent=True) or {}
    if not data.get("slug") or not data.get("title") or not data.get("theory"):
        return jsonify({"error": "Preencha: slug, título e teoria."}), 400
    import re as _re
    _UUID_RE = _re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', _re.I)
    def _safe_uuid(v):
        return v if (v and _UUID_RE.match(str(v))) else None
    payload = {
        "number":      int(data.get("number") or 0),
        "slug":        data["slug"].strip(),
        "title":       data["title"].strip(),
        "description": data.get("description", ""),
        "topics":      data.get("topics", ""),
        "group_slug":  data.get("group_slug", ""),
        "video_url":   data.get("video_url", ""),
        "theory":      data.get("theory", ""),
        "visual":      "",
        "exercises":   data.get("exercises") or [],
        "game":             data.get("game", ""),
        "game_kind":        data.get("game_kind", "game-challenge"),
        "game_data":        data.get("game_data") or {},
        "theory_audio_url": data.get("theory_audio_url", ""),
        "module_type":      data.get("module_type", "canonical"),
        "assigned_to":      data.get("assigned_to", ""),
        "created_by":       _safe_uuid(session.get("user_id")),
    }
    try:
        try:
            row = sb_upsert("modules", payload, conflict_col="slug")
        except Exception as col_exc:
            # Retry without new columns if they don't exist in DB yet
            if "module_type" in str(col_exc) or "assigned_to" in str(col_exc):
                payload.pop("module_type", None)
                payload.pop("assigned_to", None)
                row = sb_upsert("modules", payload, conflict_col="slug")
            else:
                raise
        saved = row[0] if isinstance(row, list) else row
        return jsonify({"ok": True, "module": saved}), 200
    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


def _strip_markdown(text: str) -> str:
    """Remove markdown syntax so TTS reads clean prose."""
    import re
    # Remove images ![alt](url) entirely — not readable aloud
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    # Remove links [text](url) — keep the link text only
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove headings #
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic **, *, __, _
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    text = re.sub(r'_{1,3}([^_]+)_{1,3}', r'\1', text)
    # Remove inline code `code`
    text = re.sub(r'`[^`]+`', '', text)
    # Remove code blocks ```...```
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Remove blockquotes >
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)
    # Remove horizontal rules ---/***
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Remove list markers - * +
    text = re.sub(r'^[\-\*\+]\s+', '', text, flags=re.MULTILINE)
    # Remove numbered list markers 1. 2.
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)
    # Collapse extra blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


@bp.post("/admin/generate-narration")
def admin_generate_narration():
    """Generate Google Cloud TTS narration for a module's theory, save to Storage, return URL."""
    if err := require_teacher_token():
        return err
    body        = request.get_json(silent=True) or {}
    raw_text    = (body.get("text") or "").strip()
    module_slug = (body.get("module_slug") or "").strip()
    if not raw_text or not module_slug:
        return jsonify({"error": "text e module_slug são obrigatórios"}), 400

    text = _strip_markdown(raw_text)[:5000]

    gcp_creds = current_app.config.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not gcp_creds:
        return jsonify({"error": "GOOGLE_APPLICATION_CREDENTIALS não configurada no .env"}), 503

    import os
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_creds
    try:
        from google.cloud import texttospeech as _tts
        voice_name = (body.get("voice_name") or "pt-BR-Chirp3-HD-Iapetus").strip()
        tts_client = _tts.TextToSpeechClient()
        response   = tts_client.synthesize_speech(
            input=_tts.SynthesisInput(text=text),
            voice=_tts.VoiceSelectionParams(language_code="pt-BR", name=voice_name),
            audio_config=_tts.AudioConfig(audio_encoding=_tts.AudioEncoding.MP3),
        )
        audio_bytes = response.audio_content
    except Exception as exc:
        return jsonify({"error": f"Google TTS: {exc}"}), 502

    supabase_url = current_app.config["SUPABASE_URL"]
    service_key  = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket   = "narrations"
    filename = f"{module_slug}/theory.mp3"
    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
    r = http.post(upload_url, headers={
        "apikey":        service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type":  "audio/mpeg",
        "x-upsert":      "true",
    }, data=audio_bytes, timeout=60)
    if not r.ok:
        return jsonify({"error": f"Storage: {r.status_code} {r.text}"}), 500

    public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"
    return jsonify({"url": public_url}), 200


@bp.post("/admin/upload-image")
def admin_upload_image():
    """Upload an image to Supabase Storage and return its public URL."""
    if err := require_teacher_token():
        return err
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    allowed = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
    if f.content_type not in allowed:
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400

    import uuid, os
    ext = os.path.splitext(f.filename or "img")[1] or ".jpg"
    filename = f"modules/{uuid.uuid4().hex}{ext}"

    supabase_url = current_app.config["SUPABASE_URL"]
    service_key  = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket = "module-images"

    upload_url = f"{supabase_url}/storage/v1/object/{bucket}/{filename}"
    headers = {
        "apikey":        service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type":  f.content_type,
        "x-upsert":      "true",
    }
    r = http.post(upload_url, headers=headers, data=f.read(), timeout=30)
    if not r.ok:
        return jsonify({"error": f"Supabase Storage: {r.status_code} {r.text}"}), 500

    public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{filename}"
    return jsonify({"url": public_url}), 200


@bp.post("/tts")
def tts_speak():
    """TTS proxy — ElevenLabs primary, Azure Neural fallback. Returns audio/mpeg."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Login necessário"}), 401

    body  = request.get_json(silent=True) or {}
    text  = (body.get("text") or "").strip()[:3000]
    voice = (body.get("voice") or "").strip()
    if not text:
        return jsonify({"error": "text é obrigatório"}), 400

    from flask import Response

    # ── ElevenLabs (SDK) ──────────────────────────────────────────────────────
    el_key = current_app.config.get("ELEVENLABS_KEY", "")
    if el_key:
        try:
            from elevenlabs.client import ElevenLabs as _EL
            voice_id = voice or "CstacWqMhJQlnfLPxRG4"  # default: chosen voice
            client = _EL(api_key=el_key)
            audio_gen = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
            )
            audio_bytes = b"".join(audio_gen)
            return Response(audio_bytes, content_type="audio/mpeg")
        except Exception:
            pass  # fall through to Azure

    # ── Azure Neural fallback ─────────────────────────────────────────────────
    az_key    = current_app.config.get("AZURE_SPEECH_KEY", "")
    az_region = current_app.config.get("AZURE_SPEECH_REGION", "brazilsouth")
    if az_key:
        az_voice = voice if voice.startswith("pt-BR-") else "pt-BR-FranciscaNeural"
        ssml = f"<speak version='1.0' xml:lang='pt-BR'><voice name='{az_voice}'><prosody rate='0%'>{text}</prosody></voice></speak>"
        r = http.post(
            f"https://{az_region}.tts.speech.microsoft.com/cognitiveservices/v1",
            headers={
                "Ocp-Apim-Subscription-Key": az_key,
                "Content-Type": "application/ssml+xml",
                "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
            },
            data=ssml.encode("utf-8"),
            timeout=15,
        )
        if r.ok:
            return Response(r.content, content_type="audio/mpeg")

    return jsonify({"error": "Nenhuma chave TTS configurada. Adicione ELEVENLABS_KEY ou AZURE_SPEECH_KEY no .env"}), 503


@bp.get("/tts/voices")
def tts_voices():
    """Lista vozes disponíveis do ElevenLabs."""
    if not session.get("user_id"):
        return jsonify({"error": "Login necessário"}), 401
    el_key = current_app.config.get("ELEVENLABS_KEY", "")
    if not el_key:
        return jsonify({"voices": [], "error": "ELEVENLABS_KEY não configurada"}), 200
    try:
        from elevenlabs.client import ElevenLabs as _EL
        client = _EL(api_key=el_key)
        result = client.voices.get_all()
        voices = [
            {"id": v.voice_id, "name": v.name, "category": v.category or "", "labels": dict(v.labels or {})}
            for v in result.voices
        ]
        voices.sort(key=lambda v: (v["category"] != "premade", v["name"]))
        return jsonify({"voices": voices})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


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
    from tehillim.extensions import require_teacher_token
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


@bp.delete("/admin/modulos/<slug>")
def admin_modulos_delete(slug: str):
    """Remove a module from DB — it reverts to the .md version."""
    if err := require_teacher_token():
        return err
    try:
        sb_delete("modules", {"slug": f"eq.{slug}"})
        return jsonify({"ok": True})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.post("/admin/modulos/migrate")
def admin_modulos_migrate():
    """Bulk-import all .md modules into the DB (upsert, DB takes priority after)."""
    if err := require_teacher_token():
        return err
    from tehillim.content.modules import MODULES as MD_MODULES
    imported, errors = [], []
    for m in MD_MODULES:
        try:
            theory = visual = game = ""
            game_kind = "game-challenge"
            exercises = []
            for step in m.steps:
                k, body = step.kind, step.body
                if k == "theory":
                    cut = "\n\nComo praticar:"
                    theory = body[:body.index(cut)] if cut in body else body
                elif k == "visual":
                    cut = "\n\nObserve o desenho"
                    visual = body[:body.index(cut)] if cut in body else body
                elif k.startswith("game-"):
                    game_kind = k
                    cut = "\n\nObjetivo: fixar"
                    game = body[:body.index(cut)] if cut in body else body
                elif k.startswith("exercise-"):
                    exercises.append({"kind": k, "prompt": step.prompt,
                                      "options": list(step.options), "answer": step.answer})
            payload = {
                "number": m.number, "slug": m.slug, "title": m.title,
                "description": m.description, "topics": ", ".join(m.topics),
                "group_slug": "", "video_url": "" if m.video_url == "video_placeholder_url" else (m.video_url or ""),
                "theory": theory, "visual": visual, "exercises": exercises,
                "game": game, "game_kind": game_kind,
            }
            sb_upsert("modules", payload, conflict_col="slug")
            imported.append(m.slug)
        except Exception as exc:
            errors.append({"slug": m.slug, "error": str(exc)})
    return jsonify({"imported": len(imported), "errors": errors})


@bp.get("/bona/<slug>")
def bona_sheet(slug: str):
    from pathlib import Path
    from flask import send_file
    sheet_path = Path(__file__).resolve().parent.parent / "static" / "bona" / f"{slug}.musicxml"
    if not sheet_path.exists():
        abort(404)
    return send_file(sheet_path, mimetype="application/xml")


@bp.get("/pozzoli/<slug>")
def pozzoli_sheet(slug: str):
    from pathlib import Path
    from flask import send_file
    sheet_path = Path(__file__).resolve().parent.parent / "static" / "pozzoli" / f"{slug}.musicxml"
    if not sheet_path.exists():
        abort(404)
    return send_file(sheet_path, mimetype="application/xml")


# ── Acesso do aluno ───────────────────────────────────────────────────────────

@bp.get("/my-access")
def my_access():
    if not session.get("user_id"):
        return jsonify({"slugs": [], "isTeacher": False})
    if session.get("is_teacher"):
        return jsonify({"slugs": [], "isTeacher": True})
    try:
        rows  = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{session['user_id']}"})
        slugs = [r["module_slug"] for r in rows]
        session["module_slugs"] = slugs
        return jsonify({"slugs": slugs, "isTeacher": False})
    except Exception:
        return jsonify({"slugs": session.get("module_slugs", []), "isTeacher": False})


# ── Progresso ─────────────────────────────────────────────────────────────────

@bp.post("/quiz-answer")
def save_quiz_answer():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    body = request.get_json(silent=True) or {}
    module_slug = body.get("module_slug", "").strip()
    step_index  = body.get("step_index")
    step_kind   = body.get("step_kind", "").strip()
    question    = body.get("question") or None
    answer      = body.get("answer") or None
    correct     = body.get("correct")
    if not module_slug or step_index is None:
        abort(400)
    try:
        sb_post("quiz_answers", {
            "user_id":     user_id,
            "module_slug": module_slug,
            "step_index":  int(step_index),
            "step_kind":   step_kind,
            "question":    question,
            "answer":      answer,
            "correct":     bool(correct),
        }, prefer="return=minimal")
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.post("/progress")
def save_progress():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    body        = request.get_json(silent=True) or {}
    module_slug = body.get("module_slug", "").strip()
    completed   = int(body.get("completed", 0))
    if not module_slug:
        abort(400)

    now = _now_iso()
    payload = {"user_id": user_id, "module_slug": module_slug,
               "completed": completed, "updated_at": now}

    # Set completed_at only on first completion (preserved via upsert logic)
    first_completion = False
    if completed > 0:
        existing = sb_get("module_progress", {
            "select": "completed,completed_at",
            "user_id": f"eq.{user_id}",
            "module_slug": f"eq.{module_slug}",
        })
        prev_completed = existing[0].get("completed", 0) if existing else 0
        prev_completed_at = existing[0].get("completed_at") if existing else None
        if not prev_completed_at:
            payload["completed_at"] = now
            if prev_completed == 0:
                first_completion = True

    try:
        sb_upsert("module_progress", payload, conflict_col="user_id,module_slug")
    except Exception:
        try:
            sb_post("module_progress", payload)
        except Exception:
            pass

    return jsonify({"ok": True})


@bp.get("/study-days")
def get_study_days():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"days": []}), 401
    try:
        rows = sb_get("study_days", {"select": "day", "user_id": f"eq.{user_id}", "order": "day.desc"})
        return jsonify({"days": [r["day"] for r in rows]})
    except Exception:
        return jsonify({"days": []})


@bp.post("/study-day")
def mark_study_day():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    day = _today()
    try:
        sb_post("study_days", {"user_id": user_id, "day": day})
    except Exception:
        pass
    return jsonify({"ok": True})


@bp.post("/me/name")
def update_name():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    name = (request.get_json(silent=True) or {}).get("name", "").strip()
    if not name:
        abort(400)
    session["name"] = name
    # Atualiza metadado no Supabase em background (best-effort)
    try:
        sb_put(f"/auth/v1/admin/users/{user_id}", {"user_metadata": {"name": name}})
    except Exception:
        pass
    return jsonify({"ok": True, "name": name})


# ── API Professor ─────────────────────────────────────────────────────────────

@bp.get("/teacher/students")
def teacher_students():
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        params={"per_page": 200},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"users": []})

    from collections import defaultdict
    users_raw = r.json().get("users", [])

    # Professores só vêem seus próprios alunos; owner vê todos
    if not is_owner_session():
        my_id = session.get("user_id")
        users_raw = [
            u for u in users_raw
            if (u.get("user_metadata") or {}).get("teacher_id") == my_id
        ]

    users = {
        u["id"]: {
            "email":      u["email"],
            "name":       (u.get("user_metadata") or {}).get("name") or "",
            "role":       (u.get("user_metadata") or {}).get("role") or "",
            "teacher_id": (u.get("user_metadata") or {}).get("teacher_id") or "",
        }
        for u in users_raw
    }

    try:
        progress = sb_get("module_progress", {"select": "user_id,module_slug,completed,updated_at", "order": "updated_at.desc"})
        study    = sb_get("study_days",      {"select": "user_id,day", "order": "day.desc"})
    except Exception as exc:
        result = [
            {"id": uid, "email": info["email"], "name": info["name"], "role": info["role"],
             "teacher_id": info["teacher_id"],
             "modules_completed": 0, "study_days": 0, "last_activity": None}
            for uid, info in users.items()
        ]
        return jsonify({"students": result, "warning": f"Progresso indisponível: {exc}"})

    prog_map  = defaultdict(list)
    study_map = defaultdict(list)

    for row in progress:
        prog_map[row["user_id"]].append(row)
    for row in study:
        study_map[row["user_id"]].append(row["day"])

    result = []
    for uid, info in users.items():
        result.append({
            "id": uid, "email": info["email"], "name": info["name"], "role": info["role"],
            "teacher_id":        info["teacher_id"],
            "modules_completed": sum(1 for p in prog_map[uid] if p["completed"] > 0),
            "study_days":        len(study_map[uid]),
            "last_activity":     prog_map[uid][0]["updated_at"] if prog_map[uid] else None,
        })

    result.sort(key=lambda x: x["last_activity"] or "", reverse=True)
    return jsonify({"students": result})


@bp.get("/teacher/student/<user_id>/access")
def teacher_student_access(user_id: str):
    if err := require_teacher_token():
        return err
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    try:
        rows = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{user_id}"})
        return jsonify({"slugs": [r["module_slug"] for r in rows]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.put("/teacher/student/<user_id>/access")
def teacher_sync_access(user_id: str):
    if err := require_teacher_token():
        return err
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    body  = request.get_json(silent=True) or {}
    slugs = [s.strip() for s in body.get("slugs", []) if s.strip()]
    supabase_url = current_app.config["SUPABASE_URL"]

    r = http.delete(
        f"{supabase_url}/rest/v1/student_access",
        headers=sb_headers(),
        params={"user_id": f"eq.{user_id}"},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.text}), r.status_code

    if slugs:
        rows = [{"user_id": user_id, "module_slug": s} for s in slugs]
        r = http.post(
            f"{supabase_url}/rest/v1/student_access",
            headers={**sb_headers(), "Prefer": "return=minimal"},
            json=rows,
            timeout=10,
        )
        if not r.ok:
            return jsonify({"error": r.text}), r.status_code

    return jsonify({"slugs": slugs})


@bp.post("/teacher/comments")
def teacher_add_comment():
    if err := require_teacher_token():
        return err
    body        = request.get_json(silent=True) or {}
    student_id  = body.get("student_id", "").strip()
    content     = body.get("content", "").strip()
    module_slug = body.get("module_slug") or None
    if not student_id or not content:
        abort(400)
    result = sb_post("teacher_comments", {"student_id": student_id, "content": content, "module_slug": module_slug})
    return jsonify(result[0]), 201


@bp.delete("/teacher/comments/<comment_id>")
def teacher_delete_comment(comment_id: str):
    if err := require_teacher_token():
        return err
    sb_delete("teacher_comments", {"id": f"eq.{comment_id}"})
    return "", 204


@bp.get("/teacher/student/<user_id>")
def teacher_student_detail(user_id: str):
    if err := require_teacher_token():
        return err
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    try:
        progress = sb_get("module_progress",  {"select": "module_slug,completed,updated_at", "user_id": f"eq.{user_id}", "order": "updated_at.desc"})
        study    = sb_get("study_days",       {"select": "day", "user_id": f"eq.{user_id}", "order": "day.desc"})
        comments = sb_get("teacher_comments", {"select": "id,module_slug,content,created_at", "student_id": f"eq.{user_id}", "order": "created_at.desc"})
        supabase_url = current_app.config["SUPABASE_URL"]
        r_quiz = http.get(
            f"{supabase_url}/rest/v1/quiz_answers",
            headers=sb_headers(),
            params={"select": "module_slug,question,correct", "user_id": f"eq.{user_id}"},
            timeout=10,
        )
        quiz_rows = r_quiz.json() if r_quiz.ok else []
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    from collections import Counter
    total_q   = len(quiz_rows)
    correct_q = sum(1 for q in quiz_rows if q.get("correct"))
    wrong     = [q["question"] for q in quiz_rows if not q.get("correct") and q.get("question")]
    top_errors = [{"question": q, "count": c} for q, c in Counter(wrong).most_common(10)]

    return jsonify({
        "progress":      progress,
        "study_days":    [r["day"] for r in study],
        "comments":      comments,
        "extra_lessons": get_student_extra_lessons(user_id),
        "quiz": {
            "total":     total_q,
            "correct":   correct_q,
            "accuracy":  round(correct_q / total_q * 100) if total_q > 0 else None,
            "top_errors": top_errors,
        },
    })


@bp.get("/teacher/report")
def teacher_period_report():
    if err := require_teacher_token():
        return err

    start = request.args.get("start", "").strip()
    end   = request.args.get("end",   "").strip()
    if not start or not end:
        return jsonify({"error": "Parâmetros start e end são obrigatórios"}), 400

    supabase_url = current_app.config["SUPABASE_URL"]

    r = http.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        params={"per_page": 200},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"students": []})

    users_raw = r.json().get("users", [])
    users = {
        u["id"]: {
            "email": u["email"],
            "name":  (u.get("user_metadata") or {}).get("name") or "",
            "role":  (u.get("user_metadata") or {}).get("role") or "",
        }
        for u in users_raw
    }

    end_ts = f"{end}T23:59:59"
    try:
        r_study = http.get(
            f"{supabase_url}/rest/v1/study_days",
            headers=sb_headers(),
            params=[("select", "user_id,day"), ("day", f"gte.{start}"), ("day", f"lte.{end}")],
            timeout=10,
        )
        r_study.raise_for_status()

        r_prog = http.get(
            f"{supabase_url}/rest/v1/module_progress",
            headers=sb_headers(),
            params=[("select", "user_id,module_slug,updated_at"), ("completed", "gt.0"),
                    ("updated_at", f"gte.{start}"), ("updated_at", f"lte.{end_ts}")],
            timeout=10,
        )
        r_prog.raise_for_status()

        r_quiz = http.get(
            f"{supabase_url}/rest/v1/quiz_answers",
            headers=sb_headers(),
            params=[("select", "user_id,question,correct"),
                    ("created_at", f"gte.{start}"), ("created_at", f"lte.{end_ts}")],
            timeout=10,
        )
        r_quiz.raise_for_status()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    from collections import defaultdict, Counter
    study_map = defaultdict(list)
    prog_map  = defaultdict(list)
    quiz_map  = defaultdict(list)

    for row in r_study.json():
        study_map[row["user_id"]].append(row["day"])
    for row in r_prog.json():
        prog_map[row["user_id"]].append(row)
    for row in r_quiz.json():
        quiz_map[row["user_id"]].append(row)

    result = []
    for uid, info in users.items():
        if info["role"] == "teacher":
            continue
        quiz_user = quiz_map[uid]
        total_q   = len(quiz_user)
        correct_q = sum(1 for q in quiz_user if q.get("correct"))
        wrong     = [q["question"] for q in quiz_user if not q.get("correct") and q.get("question")]
        top_errors = [{"question": q, "count": c} for q, c in Counter(wrong).most_common(5)]
        result.append({
            "id":                uid,
            "email":             info["email"],
            "name":              info["name"],
            "study_days":        len(study_map[uid]),
            "modules_completed": len(prog_map[uid]),
            "modules":           [p["module_slug"] for p in prog_map[uid]],
            "quiz_total":        total_q,
            "quiz_correct":      correct_q,
            "quiz_accuracy":     round(correct_q / total_q * 100) if total_q > 0 else None,
            "top_errors":        top_errors,
        })

    result.sort(key=lambda x: x["study_days"], reverse=True)
    return jsonify({"students": result, "period": {"start": start, "end": end}})


@bp.get("/teacher/student/<user_id>/exercises")
def teacher_student_exercises(user_id: str):
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.get(
        f"{supabase_url}/rest/v1/quiz_answers",
        headers=sb_headers(),
        params={"select": "id,module_slug,step_index,step_kind,question,answer,correct,created_at",
                "user_id": f"eq.{user_id}", "order": "created_at.desc"},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": f"Supabase {r.status_code}: {r.text}", "exercises": []}), 500
    return jsonify({"exercises": r.json()})


@bp.get("/teacher/student/<user_id>/submissions")
def teacher_student_submissions(user_id: str):
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("submissions", {"select": "id,module_slug,audio_path,status,created_at",
                                      "user_id": f"eq.{user_id}", "order": "created_at.desc"})
        return jsonify({"submissions": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.get("/teacher/student/<user_id>/messages")
def teacher_student_messages(user_id: str):
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("messages", {
            "select":     "id,sender_type,module_slug,step_index,question_preview,content,read_at,created_at",
            "student_id": f"eq.{user_id}",
            "order":      "created_at.asc",
        })
        return jsonify({"messages": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.patch("/teacher/student/<user_id>/messages/read-all")
def teacher_mark_all_student_messages_read(user_id: str):
    """Marca como lidas todas as mensagens do aluno ainda não lidas (sender_type=student)."""
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    http.patch(
        f"{supabase_url}/rest/v1/messages",
        headers={**sb_headers(), "Prefer": "return=minimal"},
        params={"student_id": f"eq.{user_id}", "sender_type": "eq.student", "read_at": "is.null"},
        json={"read_at": _now_iso()},
        timeout=10,
    )
    return "", 204


@bp.post("/teacher/student/<user_id>/messages")
def teacher_send_message(user_id: str):
    if err := require_teacher_token():
        return err
    body             = request.get_json(silent=True) or {}
    content          = body.get("content", "").strip()
    module_slug      = body.get("module_slug") or None
    step_index       = body.get("step_index")
    question_preview = (body.get("question_preview") or "").strip() or None
    if not content:
        abort(400)
    payload = {
        "student_id": user_id, "sender_type": "teacher",
        "content": content, "module_slug": module_slug,
    }
    if step_index is not None:
        payload["step_index"] = int(step_index)
    if question_preview:
        payload["question_preview"] = question_preview[:200]
    row = sb_post("messages", payload)
    return jsonify(row[0] if isinstance(row, list) else row), 201


@bp.patch("/teacher/messages/<msg_id>/read")
def teacher_mark_message_read(msg_id: str):
    if err := require_teacher_token():
        return err
    supabase_url = current_app.config["SUPABASE_URL"]
    http.patch(
        f"{supabase_url}/rest/v1/messages",
        headers={**sb_headers(), "Prefer": "return=minimal"},
        params={"id": f"eq.{msg_id}"},
        json={"read_at": _now_iso()},
        timeout=10,
    )
    return "", 204


@bp.get("/teacher/messages/unread")
def teacher_unread_messages():
    """Retorna contagem de msgs não lidas de alunos, agrupada por aluno."""
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("messages", {
            "select":      "student_id",
            "sender_type": "eq.student",
            "read_at":     "is.null",
        })
    except Exception as exc:
        return jsonify({"total": 0, "students": [], "error": str(exc)})

    from collections import Counter
    counts = Counter(r["student_id"] for r in rows)
    return jsonify({
        "total":    sum(counts.values()),
        "students": [{"id": sid, "count": c} for sid, c in counts.items()],
    })


# ── API Aluno — mensagens ──────────────────────────────────────────────────────

@bp.get("/messages")
def student_messages():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        rows = sb_get("messages", {
            "select":     "id,sender_type,module_slug,step_index,question_preview,content,read_at,created_at",
            "student_id": f"eq.{user_id}",
            "order":      "created_at.asc",
        })
        return jsonify({"messages": rows})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.post("/messages")
def student_send_message():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    body        = request.get_json(silent=True) or {}
    content     = body.get("content", "").strip()
    module_slug = body.get("module_slug") or None
    if not content:
        abort(400)
    row = sb_post("messages", {
        "student_id": user_id, "sender_type": "student",
        "content": content, "module_slug": module_slug,
    })
    return jsonify(row[0] if isinstance(row, list) else row), 201


@bp.patch("/messages/<msg_id>/read")
def student_mark_message_read(msg_id: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    supabase_url = current_app.config["SUPABASE_URL"]
    http.patch(
        f"{supabase_url}/rest/v1/messages",
        headers={**sb_headers(), "Prefer": "return=minimal"},
        params={"id": f"eq.{msg_id}", "student_id": f"eq.{user_id}"},
        json={"read_at": _now_iso()},
        timeout=10,
    )
    return "", 204


@bp.get("/messages/unread-count")
def student_unread_count():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"count": 0})
    try:
        rows = sb_get("messages", {"select": "id", "student_id": f"eq.{user_id}",
                                   "sender_type": "eq.teacher", "read_at": "is.null"})
        return jsonify({"count": len(rows)})
    except Exception:
        return jsonify({"count": 0})


@bp.get("/my-extra-lessons")
def my_extra_lessons():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({}), 401
    return jsonify(get_student_extra_lessons(user_id))


@bp.post("/teacher/student/<user_id>/extra-lessons")
def teacher_add_extra_lesson(user_id: str):
    if err := require_teacher_token():
        return err
    body = request.get_json(silent=True) or {}
    if not all(body.get(k) for k in ("module_slug", "title", "type", "url")):
        abort(400)
    lesson = add_student_extra_lesson(
        user_id=user_id,
        module_slug=body["module_slug"],
        title=body["title"],
        description=body.get("description", ""),
        content_type=body["type"],
        url=body["url"],
    )
    return jsonify(lesson), 201


@bp.delete("/teacher/student/<user_id>/extra-lessons/<lesson_id>")
def teacher_delete_extra_lesson(user_id: str, lesson_id: str):
    if err := require_teacher_token():
        return err
    if not delete_student_extra_lesson(user_id, lesson_id):
        abort(404)
    return "", 204


# ── API Admin ─────────────────────────────────────────────────────────────────

@bp.post("/admin/create-user")
def admin_create_user():
    if err := require_teacher_token():
        return err
    body       = request.get_json(silent=True) or {}
    email      = body.get("email", "").strip()
    password   = body.get("password", "").strip()
    name       = body.get("name", "").strip()
    role       = body.get("role", "aluno").strip()
    teacher_id = session.get("user_id")
    if not email or not password:
        abort(400)
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.post(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        json={"email": email, "password": password,
              "user_metadata": {"name": name, "role": role, "teacher_id": teacher_id},
              "email_confirm": True},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify(r.json()), 201


@bp.delete("/admin/delete-user/<user_id>")
def admin_delete_user(user_id: str):
    if err := require_teacher_token():
        return err
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.delete(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=sb_headers(),
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return "", 204


@bp.post("/admin/reset-password")
def admin_reset_password():
    if err := require_teacher_token():
        return err
    body      = request.get_json(silent=True) or {}
    user_id   = body.get("user_id", "").strip()
    password  = body.get("password", "").strip()
    if not user_id or not password:
        abort(400)
    err_resp, status = assert_student_owner(user_id)
    if err_resp:
        return err_resp, status
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.put(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=sb_headers(),
        json={"password": password},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify({"ok": True})


@bp.post("/admin/set-teacher/<user_id>")
def admin_set_teacher(user_id: str):
    if err := require_teacher_token():
        return err
    if not is_owner_session():
        return jsonify({"error": "Apenas o owner pode promover professores"}), 403
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.put(
        f"{supabase_url}/auth/v1/admin/users/{user_id}",
        headers=sb_headers(),
        json={"user_metadata": {"role": "teacher"}},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify({"ok": True})


# ── Relatórios ────────────────────────────────────────────────────────────────

@bp.get("/admin/reports")
def admin_reports_list():
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("reports", {
            "select": "id,title,scope,scope_label,created_at,data",
            "order": "created_at.desc",
            "limit": "50",
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    # Retorna resumo sem o data completo (só contagem)
    result = []
    for r in rows:
        d = r.get("data") or {}
        students = d.get("students") or []
        result.append({
            "id":          r["id"],
            "title":       r["title"],
            "scope":       r["scope"],
            "scope_label": r["scope_label"],
            "created_at":  r["created_at"],
            "student_count": len(students),
            "summary":     d.get("summary") or {},
        })
    return jsonify({"reports": result})


@bp.get("/admin/reports/<report_id>")
def admin_report_detail(report_id: str):
    if err := require_teacher_token():
        return err
    try:
        rows = sb_get("reports", {"select": "*", "id": f"eq.{report_id}"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
    if not rows:
        abort(404)
    return jsonify(rows[0])


@bp.post("/admin/reports/generate")
def admin_report_generate():
    if err := require_teacher_token():
        return err

    body        = request.get_json(silent=True) or {}
    scope       = body.get("scope", "all")        # all | teacher | student
    scope_ref   = body.get("scope_ref", "")       # teacher_id ou student_id
    scope_label = body.get("scope_label", "")     # nome legível
    start       = body.get("start", "").strip()
    end         = body.get("end",   "").strip()
    title       = body.get("title", "").strip()

    if not start or not end:
        return jsonify({"error": "Período obrigatório"}), 400

    supabase_url = current_app.config["SUPABASE_URL"]

    # Busca todos os usuários
    r_users = http.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        params={"per_page": 200},
        timeout=10,
    )
    if not r_users.ok:
        return jsonify({"error": "Erro ao buscar usuários"}), 500

    users_raw = r_users.json().get("users", [])
    # Monta mapa completo (inclui teacher_id para filtro)
    all_users = {
        u["id"]: {
            "email":      u.get("email", ""),
            "name":       (u.get("user_metadata") or {}).get("name") or "",
            "role":       (u.get("user_metadata") or {}).get("role") or "",
            "teacher_id": (u.get("user_metadata") or {}).get("teacher_id") or "",
        }
        for u in users_raw
    }

    # Filtra por escopo
    if scope == "teacher" and scope_ref:
        filtered_ids = {uid for uid, info in all_users.items()
                        if info["teacher_id"] == scope_ref and info["role"] not in ("teacher", "owner")}
    elif scope == "student" and scope_ref:
        filtered_ids = {scope_ref} if scope_ref in all_users else set()
    else:
        filtered_ids = {uid for uid, info in all_users.items()
                        if info["role"] not in ("teacher", "owner")}

    if not filtered_ids:
        return jsonify({"error": "Nenhum aluno encontrado para esse escopo"}), 400

    end_ts = f"{end}T23:59:59"
    try:
        r_study = http.get(f"{supabase_url}/rest/v1/study_days", headers=sb_headers(),
            params=[("select","user_id,day"),("day",f"gte.{start}"),("day",f"lte.{end}")], timeout=10)
        r_prog  = http.get(f"{supabase_url}/rest/v1/module_progress", headers=sb_headers(),
            params=[("select","user_id,module_slug,updated_at"),("completed","gt.0"),
                    ("updated_at",f"gte.{start}"),("updated_at",f"lte.{end_ts}")], timeout=10)
        r_quiz  = http.get(f"{supabase_url}/rest/v1/quiz_answers", headers=sb_headers(),
            params=[("select","user_id,question,correct"),
                    ("created_at",f"gte.{start}"),("created_at",f"lte.{end_ts}")], timeout=10)
        r_study.raise_for_status(); r_prog.raise_for_status(); r_quiz.raise_for_status()
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    from collections import defaultdict, Counter
    study_map = defaultdict(list)
    prog_map  = defaultdict(list)
    quiz_map  = defaultdict(list)
    for row in r_study.json(): study_map[row["user_id"]].append(row["day"])
    for row in r_prog.json():  prog_map[row["user_id"]].append(row["module_slug"])
    for row in r_quiz.json():  quiz_map[row["user_id"]].append(row)

    # Mapa id → nome de professores para exibir
    teacher_name_map = {uid: info["name"] or info["email"].split("@")[0]
                        for uid, info in all_users.items()
                        if info["role"] in ("teacher", "owner")}

    students_data = []
    for uid in filtered_ids:
        info = all_users[uid]
        quiz_user  = quiz_map[uid]
        total_q    = len(quiz_user)
        correct_q  = sum(1 for q in quiz_user if q.get("correct"))
        wrong      = [q["question"] for q in quiz_user if not q.get("correct") and q.get("question")]
        top_errors = [{"question": q, "count": c} for q, c in Counter(wrong).most_common(5)]
        students_data.append({
            "id":                uid,
            "name":              info["name"] or info["email"].split("@")[0],
            "email":             info["email"],
            "teacher_id":        info["teacher_id"],
            "teacher_name":      teacher_name_map.get(info["teacher_id"], ""),
            "study_days":        len(study_map[uid]),
            "modules_completed": len(prog_map[uid]),
            "modules":           prog_map[uid],
            "quiz_total":        total_q,
            "quiz_correct":      correct_q,
            "quiz_accuracy":     round(correct_q / total_q * 100) if total_q > 0 else None,
            "top_errors":        top_errors,
        })

    students_data.sort(key=lambda x: x["study_days"], reverse=True)

    total_mods = sum(s["modules_completed"] for s in students_data)
    total_days = sum(s["study_days"] for s in students_data)
    acc_vals   = [s["quiz_accuracy"] for s in students_data if s["quiz_accuracy"] is not None]

    summary = {
        "total_students":    len(students_data),
        "avg_modules":       round(total_mods / len(students_data), 1) if students_data else 0,
        "avg_study_days":    round(total_days / len(students_data), 1) if students_data else 0,
        "avg_quiz_accuracy": round(sum(acc_vals) / len(acc_vals)) if acc_vals else None,
    }

    if not title:
        from datetime import datetime
        month_label = datetime.strptime(start, "%Y-%m-%d").strftime("%B/%Y").capitalize()
        scope_part  = f"– {scope_label}" if scope_label else ""
        title = f"Relatório {scope_part} {month_label}".strip()

    report_row = {
        "title":       title,
        "scope":       scope,
        "scope_ref":   scope_ref or None,
        "scope_label": scope_label or None,
        "created_by":  session.get("user_id"),
        "data": {
            "period":   {"start": start, "end": end},
            "students": students_data,
            "summary":  summary,
        },
    }

    try:
        saved = sb_post("reports", report_row)
        if isinstance(saved, list): saved = saved[0]
        return jsonify({"ok": True, "id": saved.get("id")}), 201
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# ── Exercício do dia ─────────────────────────────────────────────────────────

@bp.get("/daily-exercise")
def get_daily_exercise():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    from datetime import date, timedelta

    today_str = _today()
    today_date = date.today()

    # Find first module completion to anchor the lookback window
    try:
        first_rows = sb_get("module_progress", {
            "select":    "completed_at",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
            "order":     "completed_at.asc",
            "limit":     "1",
        })
        first_completion = first_rows[0]["completed_at"][:10] if first_rows else None
    except Exception:
        first_completion = None

    if not first_completion:
        return jsonify({"available": False})

    # Lookback: from first completion (max 14 days ago) to today
    lookback_start = max(
        date.fromisoformat(first_completion),
        today_date - timedelta(days=14),
    )

    # Dates that should have a completion
    all_dates = []
    d = lookback_start
    while d <= today_date:
        all_dates.append(d.isoformat())
        d += timedelta(days=1)

    # Fetch which dates are already completed
    try:
        done_rows = sb_get("daily_completions", {
            "select":        "exercise_date",
            "user_id":       f"eq.{user_id}",
            "exercise_date": f"gte.{lookback_start.isoformat()}",
        })
        done_dates = {r["exercise_date"] for r in done_rows}
    except Exception:
        done_dates = set()

    pending_dates = [d for d in all_dates if d not in done_dates]
    pending_count = len(pending_dates)

    if not pending_dates:
        return jsonify({"available": True, "completed": True, "pending_count": 0})

    # Serve the oldest pending date's exercise
    target_date = pending_dates[0]
    exercise = _pick_daily_exercise(user_id, target_date)
    if not exercise:
        return jsonify({"available": False})

    return jsonify({
        "available":       True,
        "completed":       False,
        "pending_count":   pending_count,
        "exercise_date":   target_date,
        "module_slug":     exercise["module_slug"],
        "module_title":    exercise["module_title"],
        "exercise_index":  exercise["exercise_index"],
        "kind":            exercise["kind"],
        "prompt":          exercise["prompt"],
        "options":         exercise["options"],
        "answer":          exercise["answer"],
    })


@bp.post("/daily-exercise/complete")
def complete_daily_exercise():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    body = request.get_json(silent=True) or {}
    exercise_date = body.get("exercise_date") or _today()
    try:
        sb_upsert("daily_completions", {
            "user_id":        user_id,
            "exercise_date":  exercise_date,
            "module_slug":    body.get("module_slug", ""),
            "exercise_index": body.get("exercise_index", 0),
        }, conflict_col="user_id,exercise_date,module_slug")
    except Exception:
        pass
    return jsonify({"ok": True})


# ── Revisão automática (toda segunda-feira) ───────────────────────────────────
#
# Lógica: cada semana (Mon–Sun) o aluno vê revisões dos módulos concluídos
# há 7–60 dias que ainda não foram revisados nessa semana.

def _this_week_monday() -> str:
    from datetime import date, timedelta
    d = date.today()
    return (d - timedelta(days=d.weekday())).isoformat()


@bp.get("/reviews")
def get_reviews():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    from datetime import date, timedelta
    from tehillim.content import get_module

    today        = date.today()
    this_monday  = _this_week_monday()
    next_monday  = (today - timedelta(days=today.weekday()) + timedelta(weeks=1)).isoformat()

    # ── Gate: check for pending daily exercises since this Monday ─────────────
    # All days from this_monday (inclusive) to yesterday must have a completion.
    gate_start = date.fromisoformat(this_monday)
    gate_dates = []
    d = gate_start
    while d < today:
        gate_dates.append(d.isoformat())
        d += timedelta(days=1)

    if gate_dates:
        try:
            done_daily = sb_get("daily_completions", {
                "select":        "exercise_date",
                "user_id":       f"eq.{user_id}",
                "exercise_date": f"gte.{this_monday}",
            })
            done_daily_dates = {r["exercise_date"] for r in done_daily}
        except Exception:
            done_daily_dates = set()

        # Only count days where the student had at least one completed module
        # (i.e., skip dates before first module completion — already handled
        # in daily-exercise, but we apply same logic here to avoid false blocks)
        try:
            first_rows = sb_get("module_progress", {
                "select":    "completed_at",
                "user_id":   f"eq.{user_id}",
                "completed": "gt.0",
                "order":     "completed_at.asc",
                "limit":     "1",
            })
            first_completion = first_rows[0]["completed_at"][:10] if first_rows else None
        except Exception:
            first_completion = None

        if first_completion:
            pending_daily = [
                dt for dt in gate_dates
                if dt >= first_completion and dt not in done_daily_dates
            ]
        else:
            pending_daily = []

        if pending_daily:
            return jsonify({
                "blocked":        True,
                "pending_daily":  len(pending_daily),
                "this_week":      [],
                "next_monday":    next_monday,
            })

    # ── Normal review logic ───────────────────────────────────────────────────
    min_age = today - timedelta(days=7)   # completed at least 7 days ago
    max_age = today - timedelta(days=60)  # ignore older than 60 days

    try:
        progress = sb_get("module_progress", {
            "select":       "module_slug,completed_at",
            "user_id":      f"eq.{user_id}",
            "completed":    "gt.0",
            "completed_at": f"gte.{max_age.isoformat()}",
        })
    except Exception:
        progress = []

    eligible = [
        p for p in progress
        if p.get("completed_at") and p["completed_at"][:10] <= min_age.isoformat()
    ]

    if not eligible:
        return jsonify({"this_week": [], "next_monday": next_monday})

    try:
        done = sb_get("review_completions", {
            "select":        "module_slug",
            "user_id":       f"eq.{user_id}",
            "reviewed_week": f"eq.{this_monday}",
        })
        done_slugs = {d["module_slug"] for d in done}
    except Exception:
        done_slugs = set()

    pending = []
    for p in eligible:
        slug = p["module_slug"]
        if slug in done_slugs:
            continue
        mod = get_module(slug)
        pending.append({
            "id":           slug,
            "module_slug":  slug,
            "module_title": mod.title if mod else slug,
            "completed_at": p["completed_at"],
        })

    return jsonify({"this_week": pending, "next_monday": next_monday})


@bp.post("/reviews/<module_slug>/complete")
def complete_review(module_slug: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        sb_upsert("review_completions", {
            "user_id":       user_id,
            "module_slug":   module_slug,
            "reviewed_week": _this_week_monday(),
        }, conflict_col="user_id,module_slug,reviewed_week")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@bp.get("/reviews/<module_slug>/exercise")
def get_review_exercise(module_slug: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    from tehillim.content import get_module
    mod = get_module(module_slug)
    if not mod:
        return jsonify({"error": "Módulo não encontrado"}), 404

    exercises = [s for s in mod.steps if s.kind.startswith("exercise-") and s.kind != "exercise-match"]
    if not exercises:
        return jsonify({"available": False})

    # Deterministic by module + current week
    import hashlib
    seed = int(hashlib.md5(f"{module_slug}:{_this_week_monday()}".encode()).hexdigest(), 16)
    ex = exercises[seed % len(exercises)]
    return jsonify({
        "available":    True,
        "module_slug":  module_slug,
        "module_title": mod.title,
        "kind":         ex.kind,
        "prompt":       ex.prompt,
        "options":      list(ex.options),
        "answer":       ex.answer,
    })


# ── Configurações do professor ─────────────────────────────────────────────────

@bp.get("/teacher/settings")
def teacher_get_settings():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        rows = sb_get("teacher_settings", {"teacher_id": f"eq.{teacher_id}"})
        settings = {r["key"]: r["value"] for r in rows}
    except Exception:
        settings = {}
    return jsonify({"settings": settings})


@bp.post("/teacher/settings")
def teacher_save_settings():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    body = request.get_json(silent=True) or {}
    for key, value in body.items():
        try:
            sb_upsert("teacher_settings", {
                "teacher_id": teacher_id,
                "key":        str(key),
                "value":      str(value),
            }, conflict_col="teacher_id,key")
        except Exception:
            pass
    return jsonify({"ok": True})


# ── Desafio semanal ───────────────────────────────────────────────────────────

@bp.get("/weekly-challenge")
def get_weekly_challenge():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    from tehillim.extensions import get_student_teacher_id
    teacher_id = get_student_teacher_id(user_id)
    if not teacher_id:
        return jsonify({"challenge": None})

    # Current ISO week Monday
    from datetime import date
    today_d = date.today()
    week_of = (today_d - __import__('datetime').timedelta(days=today_d.weekday())).isoformat()

    try:
        challenges = sb_get("weekly_challenges", {
            "select": "id,title,description,week_of",
            "teacher_id": f"eq.{teacher_id}",
            "week_of": f"eq.{week_of}",
            "limit": "1",
        })
    except Exception:
        return jsonify({"challenge": None})

    if not challenges:
        return jsonify({"challenge": None})

    ch = challenges[0]

    # Check if student already responded
    try:
        responses = sb_get("challenge_responses", {
            "select": "id,response",
            "challenge_id": f"eq.{ch['id']}",
            "student_id":   f"eq.{user_id}",
        })
        my_response = responses[0]["response"] if responses else None
    except Exception:
        my_response = None

    return jsonify({
        "challenge": {
            "id":          ch["id"],
            "title":       ch["title"],
            "description": ch["description"],
            "week_of":     ch["week_of"],
            "my_response": my_response,
        }
    })


@bp.post("/weekly-challenge/<challenge_id>/respond")
def respond_weekly_challenge(challenge_id: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    body = request.get_json(silent=True) or {}
    response_text = (body.get("response") or "").strip()
    if not response_text:
        return jsonify({"error": "Resposta vazia"}), 400

    try:
        sb_upsert("challenge_responses", {
            "challenge_id": challenge_id,
            "student_id":   user_id,
            "response":     response_text,
        }, conflict_col="challenge_id,student_id")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"ok": True})


@bp.get("/teacher/weekly-challenges")
def teacher_list_challenges():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        challenges = sb_get("weekly_challenges", {
            "select": "id,title,description,week_of,created_at",
            "teacher_id": f"eq.{teacher_id}",
            "order":      "week_of.desc",
        })
    except Exception:
        challenges = []
    return jsonify({"challenges": challenges})


@bp.post("/teacher/weekly-challenges")
def teacher_create_challenge():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    body = request.get_json(silent=True) or {}
    title       = (body.get("title") or "").strip()
    description = (body.get("description") or "").strip()
    if not title or not description:
        return jsonify({"error": "Título e descrição obrigatórios"}), 400

    from datetime import date
    today_d = date.today()
    week_of = (today_d - __import__('datetime').timedelta(days=today_d.weekday())).isoformat()

    try:
        saved = sb_post("weekly_challenges", {
            "teacher_id":  teacher_id,
            "title":       title,
            "description": description,
            "week_of":     week_of,
        })
        if isinstance(saved, list): saved = saved[0]
        return jsonify({"ok": True, "id": saved.get("id")}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.get("/teacher/weekly-challenges/<challenge_id>/responses")
def teacher_challenge_responses(challenge_id: str):
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")

    # Verify challenge belongs to this teacher
    try:
        challenges = sb_get("weekly_challenges", {
            "select": "id,title",
            "id":         f"eq.{challenge_id}",
            "teacher_id": f"eq.{teacher_id}",
        })
        if not challenges:
            return jsonify({"error": "Não encontrado"}), 404

        responses = sb_get("challenge_responses", {
            "select": "student_id,response,created_at",
            "challenge_id": f"eq.{challenge_id}",
            "order":        "created_at.asc",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Enrich with student names
    import requests as http
    from flask import current_app
    supabase_url = current_app.config["SUPABASE_URL"]
    result = []
    for r in responses:
        name = r["student_id"]
        try:
            u = http.get(f"{supabase_url}/auth/v1/admin/users/{r['student_id']}",
                         headers=sb_headers(), timeout=5)
            if u.ok:
                meta = u.json().get("user_metadata") or {}
                name = meta.get("name") or u.json().get("email", r["student_id"])
        except Exception:
            pass
        result.append({"student_name": name, "response": r["response"], "created_at": r["created_at"]})

    return jsonify({"challenge": challenges[0], "responses": result})


# ── Módulos: status de desbloqueio ────────────────────────────────────────────

@bp.get("/module-unlock-status")
def module_unlock_status():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    # Read lock_days from teacher settings (default 3)
    LOCK_DAYS = 3
    teacher_id = get_student_teacher_id(user_id)
    if teacher_id:
        try:
            rows = sb_get("teacher_settings", {
                "select":     "value",
                "teacher_id": f"eq.{teacher_id}",
                "key":        "eq.module_lock_days",
            })
            if rows:
                LOCK_DAYS = max(0, int(rows[0]["value"]))
        except Exception:
            pass

    if LOCK_DAYS == 0:
        # Lock disabled — return everything as unlocked
        from tehillim.content.groups import GROUPS
        return jsonify({mod.slug: {"locked": False} for g in GROUPS for mod in g.modules})

    try:
        progress = sb_get("module_progress", {
            "select":   "module_slug,completed,completed_at",
            "user_id":  f"eq.{user_id}",
            "completed": "gt.0",
        })
    except Exception:
        progress = []

    # Map slug → completed_at
    completed_map = {p["module_slug"]: p.get("completed_at") for p in progress}

    from tehillim.content.groups import GROUPS
    from datetime import datetime, timezone, timedelta

    result = {}
    for group in GROUPS:
        mods = list(group.modules)
        for i, mod in enumerate(mods):
            if i == 0:
                result[mod.slug] = {"locked": False}
                continue
            prev = mods[i - 1]
            prev_completed_at = completed_map.get(prev.slug)
            if not prev_completed_at:
                # Previous not completed → locked
                result[mod.slug] = {"locked": True, "reason": "prev_not_done"}
                continue
            try:
                completed_dt = datetime.fromisoformat(prev_completed_at.replace("Z", "+00:00"))
                unlock_dt = completed_dt + timedelta(days=LOCK_DAYS)
                now = datetime.now(timezone.utc)
                if now < unlock_dt:
                    result[mod.slug] = {
                        "locked": True,
                        "unlocks_at": unlock_dt.isoformat(),
                        "days_left": max(1, (unlock_dt - now).days + 1),
                    }
                else:
                    result[mod.slug] = {"locked": False}
            except Exception:
                result[mod.slug] = {"locked": False}

    return jsonify(result)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _schedule_spaced_reviews(user_id: str, module_slug: str, completed_at_iso: str):
    """Creates spaced review entries at +2, +7, +14, +30 days."""
    from datetime import datetime, timezone, timedelta
    try:
        teacher_id = get_student_teacher_id(user_id) or ""
        base_dt = datetime.fromisoformat(completed_at_iso.replace("Z", "+00:00"))
        for days in (2, 7, 14, 30):
            scheduled = (base_dt + timedelta(days=days)).date().isoformat()
            try:
                sb_upsert("spaced_reviews", {
                    "user_id":        user_id,
                    "teacher_id":     teacher_id,
                    "module_slug":    module_slug,
                    "scheduled_date": scheduled,
                }, conflict_col="user_id,module_slug,scheduled_date")
            except Exception:
                pass
    except Exception:
        pass


def _pick_daily_exercise(user_id: str, today: str) -> dict | None:
    """Returns a deterministic exercise for user+date, from completed modules."""
    import hashlib
    from tehillim.content import get_module

    try:
        completed = sb_get("module_progress", {
            "select":    "module_slug",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
        })
    except Exception:
        return None

    if not completed:
        return None

    completed_slugs = [r["module_slug"] for r in completed]

    # Collect all exercises across completed modules
    all_exercises = []
    for slug in completed_slugs:
        mod = get_module(slug)
        if not mod:
            continue
        for i, step in enumerate(mod.steps):
            if step.kind in ("exercise-mc", "exercise-tf", "exercise-fill") and step.options:
                all_exercises.append({
                    "module_slug":  slug,
                    "module_title": mod.title,
                    "exercise_index": i,
                    "kind":    step.kind,
                    "prompt":  step.prompt,
                    "options": list(step.options),
                    "answer":  step.answer,
                })

    if not all_exercises:
        return None

    seed = int(hashlib.md5(f"{user_id}:{today}".encode()).hexdigest(), 16)
    return all_exercises[seed % len(all_exercises)]


@bp.get("/exercises-by-module")
def exercises_by_module():
    """Per-module exercise list for the student exercise page."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    import hashlib
    today = _today()

    try:
        completed = sb_get("module_progress", {
            "select":    "module_slug,completed_at",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
            "order":     "completed_at.asc",
        })
    except Exception:
        completed = []

    if not completed:
        return jsonify({"modules": []})

    completed_slugs = [r["module_slug"] for r in completed]

    # Which modules have been exercised today?
    try:
        done_today = sb_get("daily_completions", {
            "select":        "module_slug",
            "user_id":       f"eq.{user_id}",
            "exercise_date": f"eq.{today}",
        })
        done_today_slugs = {r["module_slug"] for r in done_today}
    except Exception:
        done_today_slugs = set()

    from tehillim.content import get_module

    result = []
    for slug in completed_slugs:
        mod = get_module(slug)
        if not mod:
            continue

        exercises = [
            {
                "index":   i,
                "kind":    s.kind,
                "prompt":  s.prompt,
                "options": list(s.options),
                "answer":  s.answer,
            }
            for i, s in enumerate(mod.steps)
            if s.kind in ("exercise-mc", "exercise-tf", "exercise-fill") and s.options
        ]
        if not exercises:
            continue

        seed = int(hashlib.md5(f"{user_id}:{slug}:{today}".encode()).hexdigest(), 16)
        today_local = seed % len(exercises)

        result.append({
            "module_slug":       slug,
            "module_title":      mod.title,
            "module_number":     mod.number,
            "exercises":         exercises,
            "today_local_index": today_local,
            "completed_today":   slug in done_today_slugs,
        })

    return jsonify({"modules": result})


def _fetch_standalone_for_student(user_id: str) -> list:
    """Return standalone exercises visible to this student, with completion flag."""
    try:
        teacher_id = get_student_teacher_id(user_id)

        # Always fetch exercises specifically assigned to this student
        specific = sb_get("standalone_assignments", {
            "select":     "exercise_id",
            "student_id": f"eq.{user_id}",
        })
        specific_ids = {a["exercise_id"] for a in specific}

        # If we know the teacher, also fetch "all students" assignments from that teacher
        all_ids: set = set()
        if teacher_id:
            all_asgn = sb_get("standalone_assignments", {
                "select":     "exercise_id",
                "student_id": "is.null",
            })
            candidate_ids = [a["exercise_id"] for a in all_asgn]
            if candidate_ids:
                teacher_exs = sb_get("standalone_exercises", {
                    "select":     "id",
                    "teacher_id": f"eq.{teacher_id}",
                    "id":         f"in.({','.join(candidate_ids)})",
                })
                all_ids = {e["id"] for e in teacher_exs}

        combined_ids = list(specific_ids | all_ids)
        if not combined_ids:
            return []

        exercises = sb_get("standalone_exercises", {
            "select": "id,title,prompt,game_kind,game_data",
            "id":     f"in.({','.join(combined_ids)})",
            "order":  "created_at.asc",
        })
        if not exercises:
            return []

        done_rows = sb_get("standalone_completions", {
            "select":      "exercise_id",
            "student_id":  f"eq.{user_id}",
            "exercise_id": f"in.({','.join(e['id'] for e in exercises)})",
        })
        done_ids = {d["exercise_id"] for d in done_rows}

        return [
            {**ex, "completed": ex["id"] in done_ids, "type": "standalone"}
            for ex in exercises
        ]
    except Exception:
        return []


@bp.get("/exercises-week")
def exercises_week():
    """Return the current week (Mon–Sun) with exercises per day, grouped by module."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    import hashlib
    from datetime import date, timedelta

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    week_dates = [monday + timedelta(days=i) for i in range(7)]

    # ── Standalone exercises (fetched first, independent of modules) ──────────────
    standalone_today = _fetch_standalone_for_student(user_id)

    # ── Module completions ────────────────────────────────────────────────────────
    try:
        completed = sb_get("module_progress", {
            "select":    "module_slug,completed_at",
            "user_id":   f"eq.{user_id}",
            "completed": "gt.0",
            "order":     "completed_at.asc",
        })
    except Exception:
        completed = []

    if not completed:
        # No modules yet — still return week skeleton with standalone in today's slot
        if not standalone_today:
            return jsonify({"days": [], "has_modules": False})
        DAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        DAYS_FULL  = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        days = []
        for d in week_dates:
            d_str = str(d); weekday = d.weekday()
            is_today_f = d == today
            cards = standalone_today if is_today_f else []
            days.append({
                "date": d_str, "day_short": DAYS_SHORT[weekday], "day_full": DAYS_FULL[weekday],
                "day_num": d.day, "is_today": is_today_f, "is_past": d < today, "is_future": d > today,
                "cards": [] if d > today else cards,
                "completed_count": sum(1 for c in cards if c.get("completed")),
                "total_count": len(cards),
            })
        return jsonify({"days": days, "has_modules": True})

    completed_slugs = [r["module_slug"] for r in completed]

    # Completions for the entire current week
    try:
        done_rows = sb_get("daily_completions", {
            "select":        "exercise_date,module_slug",
            "user_id":       f"eq.{user_id}",
            "exercise_date": f"gte.{monday}",
        })
        done_set = {(r["exercise_date"], r["module_slug"]) for r in done_rows}
    except Exception:
        done_set = set()

    from tehillim.content import get_module
    from datetime import datetime

    module_exercises: dict = {}
    for r in completed:
        slug = r["module_slug"]
        # Parse the date the module was completed so we can gate exercises.
        # If NULL/unparseable, treat as completed long ago so exercises always show.
        raw_ts = r.get("completed_at") or ""
        try:
            completed_date = datetime.fromisoformat(raw_ts.replace("Z", "+00:00")).date()
        except Exception:
            from datetime import date as _date
            completed_date = _date(2000, 1, 1)

        mod = get_module(slug)
        if not mod:
            continue
        exercises = [
            {
                "index":   i,
                "kind":    s.kind,
                "prompt":  s.prompt,
                "options": list(s.options),
                "answer":  s.answer,
            }
            for i, s in enumerate(mod.steps)
            if s.kind in ("exercise-mc", "exercise-tf", "exercise-fill") and s.options
        ]
        if exercises:
            module_exercises[slug] = {
                "slug":           slug,
                "title":          mod.title,
                "number":         mod.number,
                "exercises":      exercises,
                "completed_date": completed_date,   # date module was finished
            }

    if not module_exercises and not standalone_today:
        return jsonify({"days": [], "has_modules": False})

    DAYS_SHORT = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    DAYS_FULL  = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

    days = []
    for d in week_dates:
        d_str   = str(d)
        weekday = d.weekday()
        is_past    = d < today
        is_future  = d > today
        is_today_f = d == today

        day_modules = []
        for slug, m in module_exercises.items():
            # Skip exercises for days BEFORE the module was completed
            # (exercises are available from the same day of completion onwards)
            if m["completed_date"] > d:
                continue

            seed   = int(hashlib.md5(f"{user_id}:{slug}:{d_str}".encode()).hexdigest(), 16)
            ex_idx = seed % len(m["exercises"])
            ex     = m["exercises"][ex_idx]
            completed_flag = (d_str, slug) in done_set
            day_modules.append({
                "module_slug":   slug,
                "module_title":  m["title"],
                "module_number": m["number"],
                "exercise":      ex,
                "exercise_index": ex_idx,
                "completed":     completed_flag,
            })

        day_modules.sort(key=lambda x: x["module_number"])
        cards = day_modules
        completed_count = sum(1 for c in cards if c.get("completed"))
        total = len(cards)

        days.append({
            "date":            d_str,
            "day_short":       DAYS_SHORT[weekday],
            "day_full":        DAYS_FULL[weekday],
            "day_num":         d.day,
            "is_today":        is_today_f,
            "is_past":         is_past,
            "is_future":       is_future,
            "cards":           [] if is_future else cards,
            "completed_count": 0 if is_future else completed_count,
            "total_count":     total,
        })

    return jsonify({
        "days":       days,
        "has_modules": True,
        "standalone": standalone_today,   # all professor exercises, shown in Extra tab
    })


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _today() -> str:
    from datetime import date
    return date.today().isoformat()


# ── Exercícios avulsos ────────────────────────────────────────────────────────

@bp.get("/standalone-exercises")
def get_standalone_exercises():
    """Return exercises assigned to the current student (pending + completed)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401

    teacher_id = get_student_teacher_id(user_id)
    if not teacher_id:
        return jsonify({"exercises": []})

    try:
        # assignments for this student (null student_id = all students of teacher)
        assignments = sb_get("standalone_assignments", {
            "select": "exercise_id",
            "or":     f"(student_id.eq.{user_id},student_id.is.null)",
        })
        # filter only assignments from this student's teacher
        ex_ids = [a["exercise_id"] for a in assignments]
        if not ex_ids:
            return jsonify({"exercises": []})

        exercises = sb_get("standalone_exercises", {
            "select":     "id,title,prompt,game_kind,game_data,created_at",
            "teacher_id": f"eq.{teacher_id}",
            "id":         f"in.({','.join(ex_ids)})",
            "order":      "created_at.desc",
        })
    except Exception:
        return jsonify({"exercises": []})

    if not exercises:
        return jsonify({"exercises": []})

    # Which ones has this student completed?
    try:
        done = sb_get("standalone_completions", {
            "select":      "exercise_id",
            "student_id":  f"eq.{user_id}",
            "exercise_id": f"in.({','.join(e['id'] for e in exercises)})",
        })
        done_ids = {d["exercise_id"] for d in done}
    except Exception:
        done_ids = set()

    for ex in exercises:
        ex["completed"] = ex["id"] in done_ids

    return jsonify({"exercises": exercises})


@bp.post("/standalone-exercises/<ex_id>/complete")
def complete_standalone_exercise(ex_id: str):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Não autenticado"}), 401
    try:
        sb_upsert("standalone_completions", {
            "exercise_id": ex_id,
            "student_id":  user_id,
        }, conflict_col="exercise_id,student_id")
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@bp.get("/teacher/standalone-exercises")
def teacher_list_standalone_exercises():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        exercises = sb_get("standalone_exercises", {
            "select": "id,title,prompt,game_kind,game_data,created_at",
            "teacher_id": f"eq.{teacher_id}",
            "order": "created_at.desc",
        })
    except Exception:
        exercises = []
    return jsonify({"exercises": exercises})


@bp.post("/teacher/standalone-exercises")
def teacher_create_standalone_exercise():
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    body = request.get_json(silent=True) or {}

    title     = (body.get("title") or "").strip()
    prompt    = (body.get("prompt") or "").strip()
    game_kind = (body.get("game_kind") or "").strip()
    game_data = body.get("game_data") or {}
    assign_to = body.get("assign_to") or []  # list of student_ids, or [] = all

    if not title or not game_kind:
        return jsonify({"error": "Campos obrigatórios: título e tipo de jogo."}), 400

    try:
        rows = sb_post("standalone_exercises", {
            "teacher_id": teacher_id,
            "title":      title,
            "prompt":     prompt,
            "game_kind":  game_kind,
            "game_data":  game_data,
        })
        ex_id = rows[0]["id"] if rows else None
        if not ex_id:
            raise Exception("no id returned")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Create assignments
    try:
        if assign_to:
            for sid in assign_to:
                sb_post("standalone_assignments", {
                    "exercise_id": ex_id,
                    "student_id":  sid,
                })
        else:
            # null student_id = all students
            sb_post("standalone_assignments", {
                "exercise_id": ex_id,
                "student_id":  None,
            })
    except Exception:
        pass

    return jsonify({"ok": True, "id": ex_id}), 201


@bp.delete("/teacher/standalone-exercises/<ex_id>")
def teacher_delete_standalone_exercise(ex_id: str):
    if err := require_teacher_token():
        return err
    teacher_id = session.get("user_id")
    try:
        sb_delete("standalone_exercises", {
            "id":         f"eq.{ex_id}",
            "teacher_id": f"eq.{teacher_id}",
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@bp.get("/teacher/standalone-exercises/<ex_id>/responses")
def teacher_standalone_responses(ex_id: str):
    if err := require_teacher_token():
        return err
    try:
        completions = sb_get("standalone_completions", {
            "select":      "student_id,completed_at",
            "exercise_id": f"eq.{ex_id}",
        })
    except Exception:
        completions = []

    # Enrich with student names (best-effort)
    from flask import current_app
    try:
        supabase_url = current_app.config["SUPABASE_URL"]
        r = http.get(
            f"{supabase_url}/auth/v1/admin/users",
            headers=sb_headers(),
            params={"per_page": 200},
            timeout=8,
        )
        users_map = {}
        if r.ok:
            for u in r.json().get("users", []):
                name = (u.get("user_metadata") or {}).get("name") or u.get("email", u["id"])
                users_map[u["id"]] = name
    except Exception:
        users_map = {}

    result = []
    for c in completions:
        result.append({
            "student_id":   c["student_id"],
            "student_name": users_map.get(c["student_id"], c["student_id"]),
            "completed_at": c["completed_at"],
        })

    return jsonify({"responses": result})
