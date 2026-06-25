"""API pública do pacote de conteúdo."""
from tehillim.content.groups import GROUPS
from tehillim.content.helpers import STEP_KINDS
from tehillim.content.modules import MODULES
from tehillim.content.types import Exercise, ModuleGroup, StudyModule, TrailStep
from tehillim.content.extra import (
    get_student_extra_lessons,
    add_student_extra_lesson,
    delete_student_extra_lesson,
)


def get_module(slug: str) -> StudyModule | None:
    return next((m for m in MODULES if m.slug == slug), None)


def get_group(slug: str) -> ModuleGroup | None:
    return next((g for g in GROUPS if g.slug == slug), None)


def groups_payload() -> list[dict[str, object]]:
    return [g.to_payload() for g in GROUPS]


def groups_summary() -> list[dict[str, object]]:
    return [g.to_summary() for g in GROUPS]


def modules_payload() -> list[dict[str, object]]:
    return [m.to_payload() for m in MODULES]


def module_summaries() -> list[dict[str, object]]:
    return [m.to_summary() for m in MODULES]


__all__ = [
    "GROUPS", "MODULES", "STEP_KINDS",
    "Exercise", "ModuleGroup", "StudyModule", "TrailStep",
    "get_module", "get_group",
    "groups_payload", "groups_summary",
    "module_summaries", "modules_payload",
    "get_student_extra_lessons", "add_student_extra_lesson", "delete_student_extra_lesson",
]