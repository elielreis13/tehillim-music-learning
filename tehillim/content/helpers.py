from tehillim.content.types import Exercise, StudyModule, TrailStep

STEP_KINDS = {
    "theory":         "Teoria",
    "video":          "Vídeo",
    "visual":         "Visualizar",
    "exercise-mc":    "Múltipla Escolha",
    "exercise-tf":    "Verdadeiro ou Falso",
    "exercise-fill":  "Completar",
    "exercise-match": "Associação",
    "game-memory":    "Jogo de Memória",
    "game-challenge": "Desafio Final",
    "game-listen":    "Jogo de Escuta",
    "game-drag":      "Arrastar e Soltar",
    "game-sort":      "Ordenar",
    "game-quiz":      "Quiz Dinâmico",
    "game-build":     "Construir",
    "game-match":     "Associar",
}


# ── Fábricas de exercício ──────────────────────────────────────────────────────

def mc(prompt: str, options: tuple[str, ...], answer: str) -> Exercise:
    """Múltipla escolha."""
    return Exercise("exercise-mc", prompt, options, answer)


def tf(statement: str, answer: str) -> Exercise:
    """Verdadeiro ou Falso. O answer deve ser 'Verdadeiro' ou 'Falso'."""
    return Exercise("exercise-tf", statement, ("Verdadeiro", "Falso"), answer)


def fill(sentence: str, options: tuple[str, ...], answer: str) -> Exercise:
    """Completar lacuna."""
    return Exercise("exercise-fill", sentence, options, answer)


def match(prompt: str, pairs: tuple[str, ...]) -> Exercise:
    """Associação. Cada par é uma string 'esquerda → direita'."""
    return Exercise("exercise-match", prompt, pairs, "")


# ── Construtor de etapas ───────────────────────────────────────────────────────

def _youtube_embed_url(url: str) -> str:
    """Converte URL do YouTube para formato embed."""
    if "youtube.com/watch?v=" in url:
        video_id = url.split("watch?v=")[-1].split("&")[0]
        return f"https://www.youtube.com/embed/{video_id}"
    return url


def build_steps(
    module_slug: str,
    subject: str,
    theory: str,
    visual: str,
    exercises: tuple[Exercise, ...],
    game: str,
    game_kind: str,
    video_url: str = "",
    vf_data: dict | None = None,
) -> tuple[TrailStep, ...]:
    """
    Monta a sequência de etapas de um módulo:
    1. Teoria
    2. Vídeo (opcional, se video_url fornecido)
    3. Visualizar
    4. Um exercício por Exercise fornecida
    5. Jogo final
    """
    theory_body = (
        f"{theory}\n\n"
        "Como praticar: leia devagar, fale o conceito em voz alta e procure exemplos "
        "ao redor. Só avance quando conseguir explicar com suas próprias palavras."
    )
    visual_body = (
        f"{visual}\n\n"
        "Observe o desenho geral primeiro, depois os detalhes. Em música, o olho aprende "
        "a reconhecer padrões: repetição, subida, descida, duração, silêncio e tempo.\n\n"
        "Use esta etapa como laboratório: observe, compare e nomeie o que está vendo."
    )
    game_title = STEP_KINDS.get(game_kind, "Jogo")
    game_body = (
        f"{game}\n\n"
        "Objetivo: fixar o conteúdo pela prática ativa. Faça com calma e, se puder, "
        "repita mais rápido numa segunda rodada."
    )

    steps: list[TrailStep] = [
        TrailStep(
            slug=f"{module_slug}-teoria",
            title="Teoria",
            kind="theory",
            summary=f"Entenda a ideia central de {subject}.",
            body=theory_body,
            prompt="Explique a ideia em voz alta antes de concluir.",
            options=(),
            answer="",
        ),
    ]

    if video_url:
        steps.append(
            TrailStep(
                slug=f"{module_slug}-video",
                title="Vídeo",
                kind="video",
                summary=f"Assista ao vídeo sobre {subject}.",
                body=_youtube_embed_url(video_url),
                prompt="Assista ao vídeo e avance quando estiver pronto.",
                options=(),
                answer="",
            )
        )

    steps.append(
        TrailStep(
            slug=f"{module_slug}-visualizar",
            title="Visualizar",
            kind="visual",
            summary=f"Veja {subject} acontecendo na prática.",
            body=visual_body,
            prompt="Observe o exemplo, encontre o padrão e diga o nome dele.",
            options=(),
            answer="",
            vf_data=vf_data,
        ),
    )

    exercise_labels = {
        "exercise-mc":    "Múltipla Escolha",
        "exercise-tf":    "Verdadeiro ou Falso",
        "exercise-fill":  "Completar",
        "exercise-match": "Associação",
    }
    for i, ex in enumerate(exercises, 1):
        steps.append(
            TrailStep(
                slug=f"{module_slug}-ex-{i}",
                title=exercise_labels.get(ex.kind, f"Exercício {i}"),
                kind=ex.kind,
                summary="Teste seu entendimento sobre o conteúdo.",
                body="Leia com atenção e escolha a melhor resposta. Se errar, releia a teoria.",
                prompt=ex.prompt,
                options=ex.options,
                answer=ex.answer,
            )
        )

    steps.append(
        TrailStep(
            slug=f"{module_slug}-jogo",
            title=game_title,
            kind=game_kind,
            summary="Fixe o conteúdo com uma missão criativa.",
            body=game_body,
            prompt="Conclua a missão e marque esta etapa como feita.",
            options=(),
            answer="",
        )
    )

    return tuple(steps)


# ── Fábrica de módulo ──────────────────────────────────────────────────────────

def module(
    number: int,
    slug: str,
    title: str,
    description: str,
    topics: tuple[str, ...],
    theory: str,
    visual: str,
    exercises: tuple[Exercise, ...],
    game: str,
    game_kind: str,
    video_url: str = "video_placeholder_url",
    vf_data: dict | None = None,
) -> StudyModule:
    """Cria um StudyModule completo com todas as etapas montadas."""
    return StudyModule(
        number=number,
        slug=slug,
        title=title,
        description=description,
        topics=topics,
        steps=build_steps(
            module_slug=slug,
            subject=title.lower(),
            theory=theory,
            visual=visual,
            exercises=exercises,
            game=game,
            game_kind=game_kind,
            video_url=video_url,
            vf_data=vf_data,
        ),
        video_url=video_url,
    )