"""28 jogos de demonstração cobrindo todos os tipos de renderer."""

DEMO_GAMES: list[dict] = [
    # ── Teoria ────────────────────────────────────────────────────────────────
    {
        "kind": "game-word-select",
        "category": "Teoria",
        "title": "Palavra Certa",
        "description": "Clique na palavra que responde corretamente à pergunta.",
        "prompt": "Qual elemento abaixo indica a velocidade de execução de uma música?",
        "game_data": {
            "parts": [
                {"text": "O andamento", "clickable": True, "correct": True},
                {"text": "indica a velocidade, enquanto a", "clickable": False, "correct": False},
                {"text": "dinâmica", "clickable": True, "correct": False},
                {"text": "indica a intensidade e o", "clickable": False, "correct": False},
                {"text": "timbre", "clickable": True, "correct": False},
                {"text": "identifica o instrumento.", "clickable": False, "correct": False},
            ]
        },
    },
    {
        "kind": "game-fill-sentence",
        "category": "Teoria",
        "title": "Complete a Frase",
        "description": "Escolha a palavra que preenche corretamente a lacuna.",
        "prompt": "Preencha com o termo correto:",
        "game_data": {
            "before": "A ",
            "after": " é a qualidade do som que nos permite distinguir dois instrumentos tocando a mesma nota.",
            "options": ["dinâmica", "timbre", "altura", "intensidade"],
            "answer": "timbre",
        },
    },
    {
        "kind": "game-find-error",
        "category": "Teoria",
        "title": "Encontre o Erro",
        "description": "Uma das partes está errada. Clique nela.",
        "prompt": "Identifique o termo incorreto na afirmação abaixo:",
        "game_data": {
            "parts": [
                {"text": "O compasso 4/4", "error": False},
                {"text": "possui quatro tempos,", "error": False},
                {"text": "sendo o primeiro e o", "error": False},
                {"text": "segundo os tempos fortes", "error": True},
                {"text": "e os demais fracos.", "error": False},
            ]
        },
    },
    {
        "kind": "game-vote",
        "category": "Teoria",
        "title": "Qual é Correto?",
        "description": "Duas definições, apenas uma está certa. Escolha.",
        "prompt": "Qual das opções define corretamente o termo 'legato'?",
        "game_data": {
            "option_a": "Tocar as notas de forma separada e destacada.",
            "option_b": "Tocar as notas de forma suave e ligada, sem interrupção.",
            "answer": "B",
        },
    },
    {
        "kind": "game-true-false-rapid",
        "category": "Teoria",
        "title": "Verdadeiro ou Falso",
        "description": "Responda rápido: verdadeiro ou falso?",
        "prompt": "",
        "game_data": {
            "statements": [
                {"text": "O símbolo '#' chama-se sustenido e eleva a nota meio tom.", "answer": "Verdadeiro"},
                {"text": "Um compasso 3/4 tem quatro tempos.", "answer": "Falso"},
                {"text": "A clave de sol indica a posição da nota Sol na segunda linha.", "answer": "Verdadeiro"},
                {"text": "Fortíssimo (ff) é mais suave que piano (p).", "answer": "Falso"},
                {"text": "A semibreve vale quatro tempos no compasso 4/4.", "answer": "Verdadeiro"},
            ]
        },
    },
    {
        "kind": "game-hot-cold",
        "category": "Teoria",
        "title": "Quente ou Frio",
        "description": "Descubra a palavra usando as dicas uma a uma.",
        "prompt": "Qual é o nome desta figura musical?",
        "game_data": {
            "answer": "COLCHEIA",
            "hints": [
                "É uma figura de duração.",
                "Vale metade de uma semínima.",
                "Tem uma bandeira em sua haste.",
                "Começa com a letra C.",
                "Termina com 'eia'.",
            ],
        },
    },

    # ── Leitura ───────────────────────────────────────────────────────────────
    {
        "kind": "game-crossword",
        "category": "Leitura",
        "title": "Palavras Cruzadas",
        "description": "Preencha as palavras cruzadas sobre teoria musical.",
        "prompt": "Complete as palavras cruzadas:",
        "game_data": {
            "clues": [
                {"direction": "Horizontal", "clue": "Figura que vale dois tempos no 4/4", "answer": "MINIMA"},
                {"direction": "Vertical",   "clue": "Símbolo que eleva a nota meio tom", "answer": "SUSTENIDO"},
                {"direction": "Horizontal", "clue": "Símbolo que abaixa a nota meio tom", "answer": "BEMOL"},
            ]
        },
    },
    {
        "kind": "game-unscramble",
        "category": "Leitura",
        "title": "Desembaralhe",
        "description": "Organize as palavras para formar a frase correta.",
        "prompt": "Monte a definição correta:",
        "game_data": {
            "shuffled": ["é", "A", "sons", "organizada", "música", "de", "combinação"],
            "solution": ["A", "música", "é", "combinação", "organizada", "de", "sons"],
        },
    },
    {
        "kind": "game-sequence",
        "category": "Leitura",
        "title": "Qual Vem Depois?",
        "description": "Identifique a nota que falta na sequência.",
        "prompt": "Qual nota completa a escala de Dó maior?",
        "game_data": {
            "items": ["Dó", "Ré", "Mi", "Fá", "Sol", "?", "Si"],
            "blank_index": 5,
            "options": ["Lá", "Fá#", "Sol#", "Ré"],
            "answer": "Lá",
        },
    },
    {
        "kind": "game-chart-fill",
        "category": "Leitura",
        "title": "Posição na Pauta",
        "description": "Clique na posição correta da nota na pauta.",
        "prompt": "Em qual posição o Dó central aparece na clave de sol?",
        "game_data": {
            "note": "Dó central",
            "positions": [
                {"label": "Primeira linha", "correct": False, "vf_key": "E/4"},
                {"label": "1ª linha suplementar inferior", "correct": True, "vf_key": "C/4"},
                {"label": "Espaço abaixo da 1ª linha", "correct": False, "vf_key": "D/4"},
                {"label": "Segunda linha", "correct": False, "vf_key": "G/4"},
            ],
        },
    },
    {
        "kind": "game-dictation",
        "category": "Leitura",
        "title": "Ditado Rítmico",
        "description": "Veja o padrão e identifique a célula rítmica correta.",
        "prompt": "Qual célula rítmica corresponde ao padrão exibido?",
        "game_data": {
            "visual_pattern": ["●", "●", "○", "●"],
            "options": ["Colcheia pontuada + semicolcheia", "Semínima + semínima", "Colcheia + colcheia + semínima", "Três colcheias"],
            "answer": "Colcheia + colcheia + semínima",
        },
    },

    # ── Ritmo ─────────────────────────────────────────────────────────────────
    {
        "kind": "game-rhythm-tap",
        "category": "Ritmo",
        "title": "Tap do Ritmo",
        "description": "Marque os tempos fortes e os silêncios do padrão.",
        "prompt": "Siga o padrão: TAP nos tempos (●) e SILÊNCIO nos demais (○).",
        "game_data": {
            "pattern": [1, 0, 1, 1, 0, 1, 0, 0],
        },
    },
    {
        "kind": "game-speedrun",
        "category": "Ritmo",
        "title": "Corrida Musical",
        "description": "Responda o máximo de perguntas no tempo limite.",
        "prompt": "Responda rápido! Você tem 30 segundos.",
        "game_data": {
            "time_limit": 30,
            "questions": [
                {"prompt": "Quantos tempos tem uma semibreve?", "options": ["1", "2", "3", "4"], "answer": "4"},
                {"prompt": "Quantos tempos tem uma mínima?", "options": ["1", "2", "3", "4"], "answer": "2"},
                {"prompt": "Quantos tempos tem uma semínima?", "options": ["1", "2", "3", "4"], "answer": "1"},
                {"prompt": "Quantas colcheias cabem em uma semínima?", "options": ["1", "2", "3", "4"], "answer": "2"},
                {"prompt": "Quantas semicolcheias equivalem a uma semínima?", "options": ["2", "3", "4", "8"], "answer": "4"},
                {"prompt": "O compasso 3/4 tem quantos tempos?", "options": ["2", "3", "4", "6"], "answer": "3"},
                {"prompt": "Quantas colcheias cabem em um compasso 6/8?", "options": ["4", "6", "8", "3"], "answer": "6"},
                {"prompt": "Qual figura vale metade de uma semínima?", "options": ["Mínima", "Colcheia", "Semibreve", "Fusa"], "answer": "Colcheia"},
            ],
        },
    },
    {
        "kind": "game-build",
        "category": "Ritmo",
        "title": "Monte o Compasso",
        "description": "Adicione figuras para preencher exatamente o compasso.",
        "prompt": "Monte um compasso de 4/4 usando as figuras disponíveis.",
        "game_data": {
            "time_signature": "4/4",
            "target_beats": 4,
            "available": [
                {"name": "Semibreve",  "beats": 4,   "symbol": "𝅝"},
                {"name": "Mínima",     "beats": 2,   "symbol": "𝅗𝅥"},
                {"name": "Semínima",   "beats": 1,   "symbol": "♩"},
                {"name": "Colcheia",   "beats": 0.5, "symbol": "♪"},
            ],
        },
    },

    # ── Audição ───────────────────────────────────────────────────────────────
    {
        "kind": "game-identify-sound",
        "category": "Audição",
        "title": "Identifique o Instrumento",
        "description": "Leia a descrição e identifique o instrumento.",
        "prompt": "Que instrumento é descrito abaixo?",
        "game_data": {
            "description": "Produz som por meio de cordas percutidas por martelos acionados por teclas. Tem registro grave, médio e agudo e é muito utilizado na música clássica e popular.",
            "options": ["Violino", "Piano", "Guitarra", "Cravo"],
            "answer": "Piano",
        },
    },
    {
        "kind": "game-listen",
        "category": "Audição",
        "title": "Escuta Ativa",
        "description": "Com base na descrição musical, identifique o elemento.",
        "prompt": "Que elemento musical está sendo descrito?",
        "game_data": {
            "description": "Você ouve uma melodia que sobe gradualmente, cada nota mais aguda que a anterior, formando uma escala. As notas parecem 'subir degraus'.",
            "options": ["Arpejo descendente", "Escala ascendente", "Acorde perfeito", "Arpejo ascendente"],
            "answer": "Escala ascendente",
        },
    },
    {
        "kind": "game-karaoke",
        "category": "Audição",
        "title": "Karaokê Rítmico",
        "description": "Pressione TAP em cada sílaba quando ela ficar ativa.",
        "prompt": "Marque o ritmo das notas conforme aparecem:",
        "game_data": {
            "syllables": ["Dó", "Ré", "Mi", "Fá", "Sol", "Lá", "Si", "Dó"],
            "interval_ms": 600,
        },
    },

    # ── Criação ───────────────────────────────────────────────────────────────
    {
        "kind": "game-compose",
        "category": "Criação",
        "title": "Componha uma Melodia",
        "description": "Crie sua própria melodia escolhendo as notas.",
        "prompt": "Use as notas da escala de Dó maior para criar uma melodia de 8 tempos:",
        "game_data": {
            "scale": ["Dó", "Ré", "Mi", "Fá", "Sol", "Lá", "Si"],
            "slots": 8,
        },
    },
    {
        "kind": "game-story",
        "category": "Criação",
        "title": "A Orquestra",
        "description": "Leia a cena e escolha os instrumentos certos para ela.",
        "prompt": "Quais instrumentos combinam com uma música suave e pastoral?",
        "game_data": {
            "scene": "Uma manhã tranquila no campo. Pássaros cantam, o vento sopra suavemente. O compositor quer capturar essa atmosfera delicada e serena.",
            "options": [
                {"name": "Flauta",        "correct": True},
                {"name": "Bombo",         "correct": False},
                {"name": "Violino",       "correct": True},
                {"name": "Tuba",          "correct": False},
                {"name": "Oboé",          "correct": True},
                {"name": "Prato (crash)", "correct": False},
            ],
        },
    },

    # ── Revisão ───────────────────────────────────────────────────────────────
    {
        "kind": "game-teach",
        "category": "Revisão",
        "title": "Ensine com suas Palavras",
        "description": "Explique o conceito com suas próprias palavras.",
        "prompt": "Explique o que é um compasso musical e para que ele serve:",
        "game_data": {
            "min_chars": 80,
            "placeholder": "O compasso é...",
        },
    },
    {
        "kind": "game-memory",
        "category": "Revisão",
        "title": "Jogo da Memória",
        "description": "Encontre os pares de notas em português e em notação internacional.",
        "prompt": "Encontre os pares: nota em português ↔ nome internacional.",
        "game_data": {
            "pairs": [
                ["Dó", "C"],
                ["Ré", "D"],
                ["Mi", "E"],
                ["Fá", "F"],
                ["Sol", "G"],
                ["Lá", "A"],
            ],
        },
    },
    {
        "kind": "game-arrange",
        "category": "Revisão",
        "title": "Ordene as Figuras",
        "description": "Coloque as figuras em ordem crescente de duração.",
        "prompt": "Ordene as figuras musicais da mais curta para a mais longa:",
        "game_data": {
            "shuffled": ["Mínima", "Semibreve", "Semicolcheia", "Semínima", "Colcheia"],
            "solution": ["Semicolcheia", "Colcheia", "Semínima", "Mínima", "Semibreve"],
        },
    },
    {
        "kind": "game-sort",
        "category": "Revisão",
        "title": "Classifique as Dinâmicas",
        "description": "Ordene as dinâmicas do mais fraco ao mais forte.",
        "prompt": "Ordene as dinâmicas do pianíssimo ao fortíssimo:",
        "game_data": {
            "shuffled": ["Forte (f)", "Pianíssimo (pp)", "Mezzo-forte (mf)", "Fortíssimo (ff)", "Piano (p)", "Mezzo-piano (mp)"],
            "solution": ["Pianíssimo (pp)", "Piano (p)", "Mezzo-piano (mp)", "Mezzo-forte (mf)", "Forte (f)", "Fortíssimo (ff)"],
        },
    },
    {
        "kind": "game-quiz",
        "category": "Revisão",
        "title": "Quiz Musical",
        "description": "Responda as perguntas sobre teoria musical.",
        "prompt": "",
        "game_data": {
            "questions": [
                {
                    "prompt": "Qual clave é usada para instrumentos de registro agudo?",
                    "options": ["Clave de fá", "Clave de sol", "Clave de dó", "Clave de ré"],
                    "answer": "Clave de sol",
                },
                {
                    "prompt": "O que indica o numerador da fração do compasso?",
                    "options": ["O valor da figura de referência", "A quantidade de tempos por compasso", "A velocidade", "O tom"],
                    "answer": "A quantidade de tempos por compasso",
                },
                {
                    "prompt": "Quantos semitons há em uma oitava?",
                    "options": ["7", "10", "12", "14"],
                    "answer": "12",
                },
                {
                    "prompt": "Como se chama a barra com dois pontos que indica repetição?",
                    "options": ["Da capo", "Segno", "Barra de repetição", "Fine"],
                    "answer": "Barra de repetição",
                },
                {
                    "prompt": "Qual escala tem todas as notas separadas por um semitom?",
                    "options": ["Escala maior", "Escala menor", "Escala cromática", "Escala pentatônica"],
                    "answer": "Escala cromática",
                },
            ],
        },
    },
    {
        "kind": "game-drag",
        "category": "Revisão",
        "title": "Arraste e Solte",
        "description": "Arraste cada figura para seu valor correto em tempos.",
        "prompt": "Associe cada figura ao seu valor em tempos (compasso 4/4):",
        "game_data": {
            "targets": ["4 tempos", "2 tempos", "1 tempo", "½ tempo"],
            "items_shuffled": ["Semínima", "Colcheia", "Semibreve", "Mínima"],
            "solution": ["Semibreve", "Mínima", "Semínima", "Colcheia"],
        },
    },
    {
        "kind": "game-puzzle",
        "category": "Revisão",
        "title": "Monte a Escala",
        "description": "Coloque cada nota no grau correto da escala de Dó maior.",
        "prompt": "Posicione cada nota no grau correspondente da escala de Dó maior:",
        "game_data": {
            "slots": ["I grau", "II grau", "III grau", "IV grau", "V grau", "VI grau", "VII grau"],
            "pieces_shuffled": ["Mi", "Lá", "Si", "Dó", "Sol", "Fá", "Ré"],
            "solution": ["Dó", "Ré", "Mi", "Fá", "Sol", "Lá", "Si"],
        },
    },
    {
        "kind": "game-connect",
        "category": "Revisão",
        "title": "Ligue os Pares",
        "description": "Conecte cada símbolo à sua definição.",
        "prompt": "Ligue cada símbolo musical ao seu nome:",
        "game_data": {
            "left": ["#", "b", "♩", "𝄞", "ff"],
            "right_shuffled": ["Fortíssimo", "Semínima", "Sustenido", "Clave de Sol", "Bemol"],
            "pairs": {
                "#":  "Sustenido",
                "b":  "Bemol",
                "♩":  "Semínima",
                "𝄞":  "Clave de Sol",
                "ff": "Fortíssimo",
            },
        },
    },
    {
        "kind": "game-challenge",
        "category": "Revisão",
        "title": "Desafio Final",
        "description": "Complete todas as tarefas do desafio musical.",
        "prompt": "Complete o desafio:",
        "game_data": {
            "mission": "Você é um músico se preparando para uma apresentação. Verifique cada item antes de subir ao palco.",
            "checklist": [
                "Identifiquei a armadura de clave da música",
                "Reconheci o compasso e pratiquei a marcação",
                "Li a melodia em solfejo pelo menos uma vez",
                "Observei todas as marcações de dinâmica",
                "Verifiquei os acidentes ocorrentes",
                "Marquei as repetições e finais alternativos",
            ],
        },
    },
]
