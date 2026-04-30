"""
Auto-descobre todos os arquivos .py desta pasta e monta a tupla MODULES.

Cada arquivo pode exportar:
  MODULE  — um único StudyModule
  MODULES — uma lista ou tupla de StudyModules

Todos são coletados, ordenados por number e expostos como MODULES.
"""
import importlib
import pkgutil
from pathlib import Path

from tehillim.content.types import StudyModule

_HERE = Path(__file__).parent


def _load_all() -> tuple[StudyModule, ...]:
    modules: list[StudyModule] = []
    for _, name, _ in pkgutil.iter_modules([str(_HERE)]):
        if name.startswith("_"):
            continue
        mod = importlib.import_module(f"tehillim.content.modules.{name}")
        if hasattr(mod, "MODULE"):
            sm = mod.MODULE
            if isinstance(sm, StudyModule):
                modules.append(sm)
        if hasattr(mod, "MODULES"):
            for sm in mod.MODULES:
                if isinstance(sm, StudyModule):
                    modules.append(sm)

    modules.sort(key=lambda m: m.number)
    return tuple(modules)


MODULES: tuple[StudyModule, ...] = _load_all()