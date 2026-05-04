"""
Carrega módulos de estudo a partir de arquivos Markdown.

─── Formato esperado ───────────────────────────────────────────────────────────

---
number: 1
slug: o-que-e-musica
title: O que é Música?
description: Descubra o que é música e como ela faz parte da sua vida.
topics: Sons organizados, Silêncio, Emoção
video: https://www.youtube.com/watch?v=...   # opcional
game_kind: game-listen                        # padrão: game-challenge
---

## Teoria

Texto explicativo do conteúdo...

## Visual

Descrição do que o aluno vai visualizar (partitura, diagrama, etc.)...

## Exercícios

### MC
Pergunta de múltipla escolha?
- Opção errada
- Opção correta ✓
- Outra errada

### VF
Afirmação verdadeira ou falsa.
> Verdadeiro

### Fill
Frase com ___ para completar.
- palavra-errada
- palavra-certa ✓
- outra-errada

### Match
Descrição opcional da associação
- Esquerda → Direita
- Esquerda2 → Direita2

## Jogo

Descrição da missão criativa / jogo final...

────────────────────────────────────────────────────────────────────────────────
Regras rápidas:
  • Marque a resposta certa com ✓  (MC e Fill)
  • Resposta do VF: linha começando com "> "
  • Pares do Match: "- Esquerda → Direita"
  • Seções obrigatórias: Teoria, Jogo
  • Seção Exercícios é opcional (módulo sem exercícios é válido)
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from tehillim.content.helpers import fill, match, mc, module, tf
from tehillim.content.types import Exercise, StudyModule


# ── Helpers internos ──────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Minúsculas + remove acentos para comparação de nomes de seção."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


# ── Frontmatter ───────────────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        k = key.strip()
        v = value.strip()
        if "#" in v:                        # remove comentários inline
            v = v[: v.index("#")].strip()
        if k:
            result[k] = v
    return result


# ── Seções (## Heading) ───────────────────────────────────────────────────────

def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = _norm(line[3:].strip())
            buf = []
        else:
            if current is not None:
                buf.append(line)

    if current is not None:
        sections[current] = "\n".join(buf).strip()

    return sections


# ── Parsers de exercício ──────────────────────────────────────────────────────

def _parse_mc(content: str) -> Exercise:
    prompt = ""
    options: list[str] = []
    answer = ""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            marked = "✓" in line
            opt = line[2:].replace("✓", "").strip()
            options.append(opt)
            if marked:
                answer = opt
        elif not prompt:
            prompt = line
    return mc(prompt, tuple(options), answer)


def _parse_vf(content: str) -> Exercise:
    statement_parts: list[str] = []
    answer = ""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("> "):
            answer = line[2:].strip()
        else:
            statement_parts.append(line)
    return tf(" ".join(statement_parts), answer)


def _parse_fill(content: str) -> Exercise:
    sentence = ""
    options: list[str] = []
    answer = ""
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            marked = "✓" in line
            opt = line[2:].replace("✓", "").strip()
            options.append(opt)
            if marked:
                answer = opt
        elif not sentence:
            sentence = line
    return fill(sentence, tuple(options), answer)


def _parse_match(content: str) -> Exercise:
    prompt = ""
    pairs: list[str] = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- ") and "→" in line:
            pairs.append(line[2:].strip())
        elif not prompt:
            prompt = line
    return match(prompt, tuple(pairs))


_EXERCISE_PARSERS = {
    "mc":          _parse_mc,
    "vf":          _parse_vf,
    "fill":        _parse_fill,
    "completar":   _parse_fill,
    "match":       _parse_match,
    "associacao":  _parse_match,
}


def _parse_exercises(text: str) -> tuple[Exercise, ...]:
    exercises: list[Exercise] = []
    blocks = re.split(r"^### ", text, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        ex_type = _norm(lines[0].strip())
        content = "\n".join(lines[1:]).strip()
        parser = _EXERCISE_PARSERS.get(ex_type)
        if parser is None:
            raise ValueError(f"tipo de exercício desconhecido: '{lines[0].strip()}' "
                             f"(esperado: MC, VF, Fill, Match)")
        exercises.append(parser(content))
    return tuple(exercises)


# ── Entry point ───────────────────────────────────────────────────────────────

def load_md_module(path: Path) -> StudyModule:
    """Lê um arquivo .md e retorna um StudyModule completo."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        raise RuntimeError(f"[md_loader] Não foi possível ler '{path.name}': {e}") from e

    if not text.lstrip().startswith("---"):
        raise ValueError(f"[md_loader] '{path.name}': frontmatter ausente (arquivo deve começar com ---)")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"[md_loader] '{path.name}': frontmatter incompleto (falta o --- de fechamento)")

    try:
        meta = _parse_frontmatter(parts[1])
    except Exception as e:
        raise ValueError(f"[md_loader] '{path.name}': erro ao ler frontmatter — {e}") from e

    missing = [f for f in ("number", "slug", "title", "description", "topics") if f not in meta]
    if missing:
        raise ValueError(f"[md_loader] '{path.name}': campos obrigatórios ausentes: {', '.join(missing)}")

    try:
        sections = _split_sections(parts[2])

        teoria      = sections.get("teoria", "")
        visual      = sections.get("visual", "")
        exercicios  = sections.get("exercicios", "")   # "Exercícios" → normalizado
        jogo        = sections.get("jogo", "")

        if not teoria:
            raise ValueError("seção '## Teoria' não encontrada ou vazia")
        if not jogo:
            raise ValueError("seção '## Jogo' não encontrada ou vazia")

        return module(
            number      = int(meta["number"]),
            slug        = meta["slug"],
            title       = meta["title"],
            description = meta["description"],
            topics      = tuple(t.strip() for t in meta["topics"].split(",")),
            theory      = teoria,
            visual      = visual,
            exercises   = _parse_exercises(exercicios) if exercicios else (),
            game        = jogo,
            game_kind   = meta.get("game_kind", "game-challenge"),
            video_url   = meta.get("video", ""),
        )

    except (ValueError, TypeError) as e:
        raise ValueError(f"[md_loader] '{path.name}': {e}") from e
