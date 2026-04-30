from tehillim.content.modules import MODULES
from tehillim.content.types import ModuleGroup


def _by_range(lo: int, hi: int) -> tuple:
    """Filtra módulos pelo número (inclusive nos dois extremos)."""
    return tuple(m for m in MODULES if lo <= m.number <= hi)


GROUPS: tuple[ModuleGroup, ...] = (
    ModuleGroup(
        name="Musicalização Infantil",
        slug="musicalizacao-infantil",
        icon="🟢",
        description=(
            "Dê os primeiros passos na música de forma lúdica! Explore sons, silêncios, "
            "grave e agudo, forte e fraco, ritmo, pulso, andamento, notas e a escala musical."
        ),
        modules=_by_range(1, 10),
    ),
    ModuleGroup(
        name="Alfabetização Musical",
        slug="alfabetizacao-musical",
        icon="🔵",
        description=(
            "Aprenda a ler a linguagem escrita da música: pentagrama, clave de sol, "
            "notas no pentagrama, figuras rítmicas, compasso e barra de compasso."
        ),
        modules=_by_range(11, 17),
    ),
    ModuleGroup(
        name="Prática e Aplicação",
        slug="pratica-e-aplicacao",
        icon="🟡",
        description=(
            "Coloque a teoria em prática! Leitura rítmica, leitura melódica, pausas, "
            "ditado rítmico, ditado melódico, interpretação, prática instrumental e criação."
        ),
        modules=_by_range(18, 25),
    ),
    ModuleGroup(
        name="Teoria e Harmonia",
        slug="teoria-e-harmonia",
        icon="🟠",
        description=(
            "Mergulhe na teoria: sustenido, bemol, bequadro, tom e semitom, escala "
            "cromática, armadura de clave, tonalidades, escalas, intervalos, acordes, "
            "campo harmônico e cifragem."
        ),
        modules=_by_range(26, 39),
    ),
    ModuleGroup(
        name="Método Bona",
        slug="metodo-bona",
        icon="🟣",
        description=(
            "Estudo sistemático do ritmo musical baseado no clássico Método Bona. "
            "40 lições progressivas organizadas em quatro blocos (B1–B4)."
        ),
        modules=_by_range(101, 140),
    ),
    ModuleGroup(
        name="Método Pozzoli",
        slug="metodo-pozzoli",
        icon="🟣",
        description=(
            "Solfejo e leitura melódica baseados no Método Pozzoli. "
            "12 trilhas progressivas do solfejo inicial ao avançado (P1–P4)."
        ),
        modules=_by_range(201, 212),
    ),
    ModuleGroup(
        name="Leitura Avançada e Expressão",
        slug="leitura-avancada",
        icon="🔴",
        description=(
            "Leitura rítmica avançada (síncope, contratempo), leitura melódica avançada, "
            "articulação, dinâmica, frase musical e interpretação completa."
        ),
        modules=_by_range(40, 45),
    ),
)