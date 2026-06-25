"""Método Bona – Extensão — lições 41–100 (números 401–460).

As lições 33-40 já estão definidas em bona_licoes.py (133-140).
Este arquivo cobre lições 41-100 → módulos 401-460.
"""
from tehillim.content.types import StudyModule, TrailStep

_BONA_EXT_META = [
    # (number, slug, time_sig_label, block_label)
    (401, "bona-licao-41", "3/4", "B5 · Lições 33–49"),
    (402, "bona-licao-42", "3/4", "B5 · Lições 33–49"),
    (403, "bona-licao-43", "3/4", "B5 · Lições 33–49"),
    (404, "bona-licao-44", "3/4", "B5 · Lições 33–49"),
    (405, "bona-licao-45", "3/4", "B5 · Lições 33–49"),
    (406, "bona-licao-46", "3/4", "B5 · Lições 33–49"),
    (407, "bona-licao-47", "3/4", "B5 · Lições 33–49"),
    (408, "bona-licao-48", "3/4", "B5 · Lições 33–49"),
    (409, "bona-licao-49", "3/4", "B5 · Lições 33–49"),
    (410, "bona-licao-50", "4/4", "B6 · Lições 50–66"),
    (411, "bona-licao-51", "4/4", "B6 · Lições 50–66"),
    (412, "bona-licao-52", "4/4", "B6 · Lições 50–66"),
    (413, "bona-licao-53", "4/4", "B6 · Lições 50–66"),
    (414, "bona-licao-54", "4/4", "B6 · Lições 50–66"),
    (415, "bona-licao-55", "4/4", "B6 · Lições 50–66"),
    (416, "bona-licao-56", "4/4", "B6 · Lições 50–66"),
    (417, "bona-licao-57", "4/4", "B6 · Lições 50–66"),
    (418, "bona-licao-58", "4/4", "B6 · Lições 50–66"),
    (419, "bona-licao-59", "4/4", "B6 · Lições 50–66"),
    (420, "bona-licao-60", "4/4", "B6 · Lições 50–66"),
    (421, "bona-licao-61", "4/4", "B6 · Lições 50–66"),
    (422, "bona-licao-62", "4/4", "B6 · Lições 50–66"),
    (423, "bona-licao-63", "4/4", "B6 · Lições 50–66"),
    (424, "bona-licao-64", "4/4", "B6 · Lições 50–66"),
    (425, "bona-licao-65", "4/4", "B6 · Lições 50–66"),
    (426, "bona-licao-66", "4/4", "B6 · Lições 50–66"),
    (427, "bona-licao-67", "6/8", "B7 · Lições 67–83"),
    (428, "bona-licao-68", "6/8", "B7 · Lições 67–83"),
    (429, "bona-licao-69", "6/8", "B7 · Lições 67–83"),
    (430, "bona-licao-70", "6/8", "B7 · Lições 67–83"),
    (431, "bona-licao-71", "6/8", "B7 · Lições 67–83"),
    (432, "bona-licao-72", "6/8", "B7 · Lições 67–83"),
    (433, "bona-licao-73", "6/8", "B7 · Lições 67–83"),
    (434, "bona-licao-74", "6/8", "B7 · Lições 67–83"),
    (435, "bona-licao-75", "6/8", "B7 · Lições 67–83"),
    (436, "bona-licao-76", "6/8", "B7 · Lições 67–83"),
    (437, "bona-licao-77", "6/8", "B7 · Lições 67–83"),
    (438, "bona-licao-78", "6/8", "B7 · Lições 67–83"),
    (439, "bona-licao-79", "6/8", "B7 · Lições 67–83"),
    (440, "bona-licao-80", "6/8", "B7 · Lições 67–83"),
    (441, "bona-licao-81", "6/8", "B7 · Lições 67–83"),
    (442, "bona-licao-82", "6/8", "B7 · Lições 67–83"),
    (443, "bona-licao-83", "6/8", "B7 · Lições 67–83"),
    (444, "bona-licao-84", "12/8", "B8 · Lições 84–100"),
    (445, "bona-licao-85", "12/8", "B8 · Lições 84–100"),
    (446, "bona-licao-86", "12/8", "B8 · Lições 84–100"),
    (447, "bona-licao-87", "12/8", "B8 · Lições 84–100"),
    (448, "bona-licao-88", "12/8", "B8 · Lições 84–100"),
    (449, "bona-licao-89", "12/8", "B8 · Lições 84–100"),
    (450, "bona-licao-90", "12/8", "B8 · Lições 84–100"),
    (451, "bona-licao-91", "12/8", "B8 · Lições 84–100"),
    (452, "bona-licao-92", "12/8", "B8 · Lições 84–100"),
    (453, "bona-licao-93", "12/8", "B8 · Lições 84–100"),
    (454, "bona-licao-94", "12/8", "B8 · Lições 84–100"),
    (455, "bona-licao-95", "12/8", "B8 · Lições 84–100"),
    (456, "bona-licao-96", "12/8", "B8 · Lições 84–100"),
    (457, "bona-licao-97", "12/8", "B8 · Lições 84–100"),
    (458, "bona-licao-98", "12/8", "B8 · Lições 84–100"),
    (459, "bona-licao-99", "12/8", "B8 · Lições 84–100"),
    (460, "bona-licao-100", "12/8", "B8 · Lições 84–100"),
]


def _make(number, slug, ts_label, block_label):
    lesson = number - 360
    return StudyModule(
        number=number,
        slug=slug,
        title=f"Bona — Lição {lesson} ({ts_label})",
        description=(
            f"Lição {lesson} do Método Bona em compasso {ts_label}. "
            f"12 compassos · {block_label}."
        ),
        topics=("Método Bona", "Ritmo", f"Compasso {ts_label}"),
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


MODULES = tuple(
    _make(num, slug, ts, label)
    for num, slug, ts, label in _BONA_EXT_META
)
