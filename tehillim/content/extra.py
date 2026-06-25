"""Extra lessons storage: {user_id: {module_slug: [lessons]}}."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

_LESSONS_FILE = Path(__file__).resolve().parent / "extra" / "lessons.json"


def _load() -> dict:
    try:
        return json.loads(_LESSONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    _LESSONS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_student_extra_lessons(user_id: str) -> dict[str, list[dict]]:
    """Returns {module_slug: [lesson, ...]} for the given student."""
    return _load().get(user_id, {})


def add_student_extra_lesson(
    user_id: str,
    module_slug: str,
    title: str,
    description: str,
    content_type: str,
    url: str,
) -> dict:
    data = _load()
    lesson = {
        "id": str(uuid.uuid4()),
        "module_slug": module_slug,
        "title": title,
        "description": description,
        "type": content_type,  # video | pdf | link
        "url": url,
    }
    data.setdefault(user_id, {}).setdefault(module_slug, []).append(lesson)
    _save(data)
    return lesson


def delete_student_extra_lesson(user_id: str, lesson_id: str) -> bool:
    data = _load()
    user_data = data.get(user_id, {})
    changed = False
    for slug in list(user_data.keys()):
        before = len(user_data[slug])
        user_data[slug] = [l for l in user_data[slug] if l["id"] != lesson_id]
        if len(user_data[slug]) < before:
            changed = True
        if not user_data[slug]:
            del user_data[slug]
    if changed:
        if user_data:
            data[user_id] = user_data
        elif user_id in data:
            del data[user_id]
        _save(data)
    return changed
