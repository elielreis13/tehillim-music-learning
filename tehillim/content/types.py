from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class TrailStep:
    """Uma etapa dentro de um módulo de estudo."""
    slug: str
    title: str
    kind: str
    summary: str
    body: str
    prompt: str
    options: tuple[str, ...]
    answer: str
    vf_data: dict | None = None

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Exercise:
    """Um exercício usado como entrada para criar uma TrailStep."""
    kind: str  # exercise-mc | exercise-tf | exercise-fill | exercise-match
    prompt: str
    options: tuple[str, ...]
    answer: str


@dataclass(frozen=True)
class StudyModule:
    """Um módulo completo com suas etapas."""
    number: int
    slug: str
    title: str
    description: str
    topics: tuple[str, ...]
    steps: tuple[TrailStep, ...]
    video_url: str = "video_placeholder_url"

    def to_summary(self) -> dict[str, object]:
        """Retorna dados do módulo SEM as etapas (leve, para listas)."""
        return {
            "number": self.number,
            "slug": self.slug,
            "title": self.title,
            "description": self.description,
            "topics": list(self.topics),
            "step_count": len(self.steps),
            "video_url": self.video_url,
        }

    def to_payload(self) -> dict[str, object]:
        """Retorna dados completos COM as etapas (para a API do módulo)."""
        return {**self.to_summary(), "steps": [s.to_payload() for s in self.steps]}


@dataclass(frozen=True)
class ModuleGroup:
    """Um grupo que agrupa vários módulos relacionados."""
    name: str
    slug: str
    icon: str
    description: str
    modules: tuple[StudyModule, ...]

    def to_summary(self) -> dict[str, object]:
        return {
            "name": self.name,
            "slug": self.slug,
            "icon": self.icon,
            "description": self.description,
            "module_count": len(self.modules),
            "modules": [m.to_summary() for m in self.modules],
        }

    def to_payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "module_count": len(self.modules),
            "modules": [m.to_payload() for m in self.modules],
        }