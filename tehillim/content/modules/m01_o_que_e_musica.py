from tehillim.content.helpers import fill, match, mc, module, tf

MODULE = module(
    1, "o-que-e-musica", "O que é Música?",
    "Descubra o que é música e como ela faz parte da sua vida.",
    ("Sons organizados", "Silêncio", "Emoção"),
    theory=(
        "Música é a arte de organizar sons e silêncios para criar algo bonito e expressivo. "
        "Quando você bate palmas em ritmo ou assobia uma melodia, já está fazendo música! "
        "Toda música tem três ingredientes: sons que você ouve, silêncios entre eles e um ritmo "
        "que os organiza no tempo. A música existe em todos os países do mundo — ela é universal!"
    ),
    visual=(
        "Uma onda sonora colorida: os picos representam sons e os vales representam silêncios. "
        "As cores variam do azul (suave) ao vermelho (intenso), mostrando que a música é cheia de emoção."
    ),
    exercises=(
        mc(
            "Qual das opções melhor define música?",
            ("Ruído aleatório de carros na rua", "Sons e silêncios organizados no tempo",
             "Qualquer barulho que você escuta", "Apenas sons tocados por instrumentos"),
            "Sons e silêncios organizados no tempo",
        ),
        tf("O silêncio NÃO faz parte da música — só os sons importam.", "Falso"),
        fill(
            "Uma música é feita de sons, ___ e um ritmo que os organiza.",
            ("silêncios", "instrumentos", "palavras"),
            "silêncios",
        ),
    ),
    game=(
        "CAÇA AOS SONS: Fique em silêncio por 30 segundos e preste atenção em tudo ao redor. "
        "Identifique 3 sons diferentes. Algum poderia fazer parte de uma música? "
        "Em seguida, bata palmas criando um padrão que se repita — você acabou de compor um ritmo!"
    ),
    game_kind="game-listen",
    video_url="https://www.youtube.com/watch?v=mKSymJVMi7k",
)