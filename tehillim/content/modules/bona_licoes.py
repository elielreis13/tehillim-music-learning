"""Método Bona — 40 lições (números 101–140)."""
from tehillim.content.types import StudyModule, TrailStep

_BONA_META = [
    # (number, slug, title, group_label)
    (101, "bona-licao-01", "Bona — Lição 1",  "B1 · Lições 1–10"),
    (102, "bona-licao-02", "Bona — Lição 2",  "B1 · Lições 1–10"),
    (103, "bona-licao-03", "Bona — Lição 3",  "B1 · Lições 1–10"),
    (104, "bona-licao-04", "Bona — Lição 4",  "B1 · Lições 1–10"),
    (105, "bona-licao-05", "Bona — Lição 5",  "B1 · Lições 1–10"),
    (106, "bona-licao-06", "Bona — Lição 6",  "B1 · Lições 1–10"),
    (107, "bona-licao-07", "Bona — Lição 7",  "B1 · Lições 1–10"),
    (108, "bona-licao-08", "Bona — Lição 8",  "B1 · Lições 1–10"),
    (109, "bona-licao-09", "Bona — Lição 9",  "B1 · Lições 1–10"),
    (110, "bona-licao-10", "Bona — Lição 10", "B1 · Lições 1–10"),
    (111, "bona-licao-11", "Bona — Lição 11", "B2 · Lições 11–20"),
    (112, "bona-licao-12", "Bona — Lição 12", "B2 · Lições 11–20"),
    (113, "bona-licao-13", "Bona — Lição 13", "B2 · Lições 11–20"),
    (114, "bona-licao-14", "Bona — Lição 14", "B2 · Lições 11–20"),
    (115, "bona-licao-15", "Bona — Lição 15", "B2 · Lições 11–20"),
    (116, "bona-licao-16", "Bona — Lição 16", "B2 · Lições 11–20"),
    (117, "bona-licao-17", "Bona — Lição 17", "B2 · Lições 11–20"),
    (118, "bona-licao-18", "Bona — Lição 18", "B2 · Lições 11–20"),
    (119, "bona-licao-19", "Bona — Lição 19", "B2 · Lições 11–20"),
    (120, "bona-licao-20", "Bona — Lição 20", "B2 · Lições 11–20"),
    (121, "bona-licao-21", "Bona — Lição 21", "B3 · Lições 21–30"),
    (122, "bona-licao-22", "Bona — Lição 22", "B3 · Lições 21–30"),
    (123, "bona-licao-23", "Bona — Lição 23", "B3 · Lições 21–30"),
    (124, "bona-licao-24", "Bona — Lição 24", "B3 · Lições 21–30"),
    (125, "bona-licao-25", "Bona — Lição 25", "B3 · Lições 21–30"),
    (126, "bona-licao-26", "Bona — Lição 26", "B3 · Lições 21–30"),
    (127, "bona-licao-27", "Bona — Lição 27", "B3 · Lições 21–30"),
    (128, "bona-licao-28", "Bona — Lição 28", "B3 · Lições 21–30"),
    (129, "bona-licao-29", "Bona — Lição 29", "B3 · Lições 21–30"),
    (130, "bona-licao-30", "Bona — Lição 30", "B3 · Lições 21–30"),
    (131, "bona-licao-31", "Bona — Lição 31", "B4 · Lições 31–40"),
    (132, "bona-licao-32", "Bona — Lição 32", "B4 · Lições 31–40"),
    (133, "bona-licao-33", "Bona — Lição 33", "B4 · Lições 31–40"),
    (134, "bona-licao-34", "Bona — Lição 34", "B4 · Lições 31–40"),
    (135, "bona-licao-35", "Bona — Lição 35", "B4 · Lições 31–40"),
    (136, "bona-licao-36", "Bona — Lição 36", "B4 · Lições 31–40"),
    (137, "bona-licao-37", "Bona — Lição 37", "B4 · Lições 31–40"),
    (138, "bona-licao-38", "Bona — Lição 38", "B4 · Lições 31–40"),
    (139, "bona-licao-39", "Bona — Lição 39", "B4 · Lições 31–40"),
    (140, "bona-licao-40", "Bona — Lição 40", "B4 · Lições 31–40"),
]


def _blank(number: int, slug: str, title: str, group_label: str) -> StudyModule:
    return StudyModule(
        number=number,
        slug=slug,
        title=title,
        description=f"Lição {number - 100} do Método Bona · {group_label}.",
        topics=("Método Bona", "Ritmo", "Leitura rítmica"),
        steps=(
            TrailStep(
                slug=f"{slug}-partitura",
                title="Partitura",
                kind="theory",
                summary="Estude a partitura desta lição com o player.",
                body="Use o player abaixo para ouvir e acompanhar a lição.",
                prompt="Leia a partitura e marque quando estiver pronto.",
                options=(),
                answer="",
            ),
        ),
        video_url="",
    )


MODULES: tuple[StudyModule, ...] = tuple(
    _blank(n, s, t, g) for n, s, t, g in _BONA_META
)
