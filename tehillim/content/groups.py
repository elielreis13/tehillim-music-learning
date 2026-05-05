from tehillim.content.modules import MODULES
from tehillim.content.types import ModuleGroup


def _by_range(lo: int, hi: int) -> tuple:
    """Filtra módulos pelo número (inclusive nos dois extremos)."""
    return tuple(m for m in MODULES if lo <= m.number <= hi)


def _by_ranges(*ranges: tuple[int, int]) -> tuple:
    """Filtra módulos por múltiplos intervalos, mantendo a ordem global."""
    return tuple(
        m
        for m in MODULES
        if any(lo <= m.number <= hi for lo, hi in ranges)
    )


GROUPS: tuple[ModuleGroup, ...] = (
    ModuleGroup(
        name="Fundamentos do Som e da Música",
        slug="fundamentos-do-som",
        icon="🎵",
        icon_file="fundamentos-do-som.svg",
        description=(
            "Ponto de partida para quem nunca estudou música formalmente. "
            "Desperte a percepção sonora, conheça as notas, o pulso e os instrumentos."
        ),
        modules=_by_range(1, 15),
    ),
    ModuleGroup(
        name="Musicalização e Iniciação Musical",
        slug="musicalizacao-iniciacao",
        icon="🟢",
        icon_file="musicalizacao-infantil.svg",
        description=(
            "Ritmo com o corpo, melodia e canto, primeiros passos na notação, pausas "
            "e compassos — tudo de forma prática antes de entrar na teoria avançada."
        ),
        modules=_by_range(16, 30),
    ),
    ModuleGroup(
        name="Alfabetização Musical Avançada",
        slug="alfabetizacao-musical",
        icon="🔵",
        icon_file="alfebatizacao-musical.svg",
        description=(
            "Acidentes, armaduras de clave, círculo das quintas, sinais de repetição, "
            "articulação, ornamentos e toda a simbologia para ler qualquer partitura."
        ),
        modules=_by_range(31, 42),
    ),
    ModuleGroup(
        name="Ritmo: Do Básico ao Complexo",
        slug="ritmo-basico-ao-complexo",
        icon="🟡",
        icon_file="pratica-aplicacao.svg",
        description=(
            "Célula rítmica, compassos compostos, síncope, contratempo, quiálteras, "
            "polirritmo, hemiola e leitura rítmica à primeira vista."
        ),
        modules=_by_range(43, 60),
    ),
    ModuleGroup(
        name="Melodia e Solfejo",
        slug="melodia-e-solfejo",
        icon="🟠",
        icon_file="teoria-harmonia.svg",
        description=(
            "Solfejo fixo, leitura melódica, entonação, afinação em conjunto, "
            "saltos melódicos e melodias cromáticas progressivas."
        ),
        modules=_by_range(61, 69),
    ),
    ModuleGroup(
        name="Dinâmica, Articulação e Expressão",
        slug="dinamica-articulacao-expressao",
        icon="🎭",
        icon_file="expressao-musical.svg",
        description=(
            "Escala dinâmica, fraseado, equilíbrio em conjunto, legato, staccato, "
            "marcato, estilos históricos, rubato e escuta ativa."
        ),
        modules=_by_ranges((94, 99), (141, 143)),
    ),
    ModuleGroup(
        name="Intervalos e Escalas",
        slug="intervalos-e-escalas",
        icon="🔷",
        icon_file="intervalos-escalas.svg",
        description=(
            "Quantidade e qualidade dos intervalos, trítono, inversões, "
            "escalas maior, menores e pentatônicas, e os 7 modos eclesiásticos."
        ),
        modules=_by_range(70, 78),
    ),
    ModuleGroup(
        name="Harmonia e Acordes",
        slug="harmonia-e-acordes",
        icon="🎹",
        icon_file="harmonia-acordes.svg",
        description=(
            "Tríades, campo harmônico maior e menor, progressões, cadências, "
            "dominantes secundárias, cifragem americana e Nashville Number System."
        ),
        modules=_by_range(79, 90),
    ),
    ModuleGroup(
        name="Tonalidade e Análise",
        slug="tonalidade-e-analise",
        icon="🔬",
        icon_file="analise-formal.svg",
        description=(
            "Forma musical (verso, refrão, ponte), período e frase, "
            "contraponto básico e reharmonização."
        ),
        modules=_by_range(91, 93),
    ),
    ModuleGroup(
        name="Método Bona",
        slug="metodo-bona",
        icon="🟣",
        icon_file="bona.svg",
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
        icon_file="pozzoli.svg",
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
        icon_file="leitura-avancada.svg",
        description=(
            "Leitura rítmica avançada (síncope, contratempo), leitura melódica avançada, "
            "articulação, dinâmica, frase musical e interpretação completa."
        ),
        modules=_by_range(144, 146),
    ),
)
