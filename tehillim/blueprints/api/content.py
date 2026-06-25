from __future__ import annotations

from flask import abort, current_app, jsonify, request, session
import requests as http

from . import bp
from tehillim.content import (
    get_module, groups_summary, modules_payload,
)
from tehillim.extensions import (
    sb_delete, sb_get, sb_headers, sb_post, sb_upsert,
    require_teacher_token,
)


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


@bp.get("/bona/<slug>")
def bona_sheet(slug: str):
    from pathlib import Path
    from flask import send_file
    sheet_path = Path(__file__).resolve().parent.parent.parent / "static" / "bona" / f"{slug}.musicxml"
    if not sheet_path.exists():
        abort(404)
    return send_file(sheet_path, mimetype="application/xml")


@bp.get("/pozzoli/<slug>")
def pozzoli_sheet(slug: str):
    from pathlib import Path
    from flask import send_file
    sheet_path = Path(__file__).resolve().parent.parent.parent / "static" / "pozzoli" / f"{slug}.musicxml"
    if not sheet_path.exists():
        abort(404)
    return send_file(sheet_path, mimetype="application/xml")


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
