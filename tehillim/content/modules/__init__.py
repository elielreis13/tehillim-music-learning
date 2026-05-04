"""
Auto-descobre módulos desta pasta e monta a tupla MODULES.

Suporta duas fontes (em ordem de prioridade):
  1. Arquivos .md  — lidos pelo md_loader (formato recomendado)
  2. Arquivos .py  — cada arquivo exporta MODULE ou MODULES

Se um número de módulo já foi carregado via .md, o .py correspondente é ignorado.
Todos os módulos são ordenados por number e expostos como MODULES.
"""
from __future__ import annotations

import importlib
import pkgutil
import warnings
from pathlib import Path

from tehillim.content.types import StudyModule

_HERE = Path(__file__).parent


def _load_all() -> tuple[StudyModule, ...]:
    modules: list[StudyModule] = []
    loaded_numbers: set[int] = set()

    # ── 1. Arquivos .md (prioridade) ──────────────────────────────────────────
    from tehillim.content.md_loader import load_md_module

    for md_path in sorted(_HERE.glob("*.md")):
        if md_path.name.startswith("_"):
            continue
        try:
            sm = load_md_module(md_path)
            modules.append(sm)
            loaded_numbers.add(sm.number)
        except Exception as exc:
            warnings.warn(str(exc), stacklevel=2)

    # ── 2. Arquivos .py (somente números ainda não carregados) ────────────────
    for _, name, _ in pkgutil.iter_modules([str(_HERE)]):
        if name.startswith("_"):
            continue
        mod = importlib.import_module(f"tehillim.content.modules.{name}")
        if hasattr(mod, "MODULE"):
            sm = mod.MODULE
            if isinstance(sm, StudyModule) and sm.number not in loaded_numbers:
                modules.append(sm)
                loaded_numbers.add(sm.number)
        if hasattr(mod, "MODULES"):
            for sm in mod.MODULES:
                if isinstance(sm, StudyModule) and sm.number not in loaded_numbers:
                    modules.append(sm)
                    loaded_numbers.add(sm.number)

    modules.sort(key=lambda m: m.number)
    return tuple(modules)


MODULES: tuple[StudyModule, ...] = _load_all()
