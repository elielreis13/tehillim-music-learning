from __future__ import annotations

from flask import current_app, jsonify, request, session
import requests as http

from . import bp
from tehillim.extensions import require_teacher_token
from .content import _strip_markdown


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
        from xml.sax.saxutils import escape as _xml_escape
        _AZ_VOICE_RE = __import__('re').compile(r'^pt-BR-[A-Za-z0-9]+(?:Neural|HD)?$')
        az_voice = voice if _AZ_VOICE_RE.match(voice or "") else "pt-BR-FranciscaNeural"
        ssml = f"<speak version='1.0' xml:lang='pt-BR'><voice name='{az_voice}'><prosody rate='0%'>{_xml_escape(text)}</prosody></voice></speak>"
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
