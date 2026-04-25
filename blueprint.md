# Blueprint — Tehillim: Plataforma de Aprendizado Musical

> Guia completo e detalhado para recriar este projeto do zero.
> Escrito para quem não tem experiência prévia com as tecnologias usadas.

---

## O que vamos construir

Uma plataforma web para ensino de música chamada **Tehillim**. Ela possui:

- Login e logout com e-mail e senha (ou magic link)
- Módulos de estudo com trilha de etapas (teoria → vídeo → visual → exercícios → jogo)
- Progresso salvo na nuvem por aluno
- Controle de acesso: professor libera módulos para cada aluno
- Painel do professor para acompanhar progresso, ouvir gravações e comentar
- Painel admin para criar e gerenciar usuários
- Método Bona: partituras em MusicXML renderizadas no navegador com player de áudio
- Conquistas, desempenho, sequência de dias de estudo

**Tecnologias:**
- **Python + Flask** — servidor web
- **Supabase** — banco de dados PostgreSQL + autenticação + armazenamento de arquivos
- **Jinja2** — templates HTML (embutido no Flask)
- **Tailwind CSS via CDN** — estilização
- **JavaScript puro** — lógica do lado do cliente (sem React, sem frameworks)
- **VexFlow** — renderização de partituras musicais
- **OSMD (OpenSheetMusicDisplay)** — renderização de arquivos MusicXML
- **Tone.js** — síntese de áudio no navegador

---

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Criar conta e projeto no Supabase](#2-criar-conta-e-projeto-no-supabase)
3. [Estrutura de pastas](#3-estrutura-de-pastas)
4. [Ambiente Python](#4-ambiente-python)
5. [Arquivo de configuração](#5-arquivo-de-configuração)
6. [Ponto de entrada da aplicação](#6-ponto-de-entrada-da-aplicação)
7. [Sistema de conteúdo (módulos e grupos)](#7-sistema-de-conteúdo-módulos-e-grupos)
8. [Rotas Flask (Blueprints)](#8-rotas-flask-blueprints)
   - [8.5 Controle de acesso: páginas do professor](#85--controle-de-acesso-páginas-exclusivas-do-professor)
9. [Banco de dados no Supabase](#9-banco-de-dados-no-supabase)
10. [Templates base HTML](#10-templates-base-html)
11. [JavaScript: autenticação (auth.js)](#11-javascript-autenticação-authjs)
12. [JavaScript: trilha de estudo (app.js)](#12-javascript-trilha-de-estudo-appjs)
13. [JavaScript: áudio (audio.js)](#13-javascript-áudio-audiojs)
14. [JavaScript: partituras (vexflow-utils.js)](#14-javascript-partituras-vexflow-utilsjs)
15. [JavaScript: gravações (recorder.js)](#15-javascript-gravações-recorderjs)
16. [Páginas principais (templates)](#16-páginas-principais-templates)
17. [CSS: estilos globais](#17-css-estilos-globais)
18. [Primeiro teste: rodar localmente](#18-primeiro-teste-rodar-localmente)
19. [Como adicionar conteúdo ao site](#19-como-adicionar-conteúdo-ao-site)
    - [19.1 Módulo regular](#191--adicionar-um-módulo-regular-teoria-musical)
    - [19.2 Grupos de módulos](#192--como-os-grupos-são-definidos)
20. [Método Bona (partituras com player)](#20-método-bona-partituras-com-player)
    - [20.5 Método Pozzoli (solfejo)](#205--método-pozzoli-solfejo)
21. [Dashboard do professor](#21-dashboard-do-professor)
22. [Painel admin](#22-painel-admin)
23. [Ordem final de montagem](#23-ordem-final-de-montagem)
24. [Deploy na internet (Google Cloud Run)](#24-deploy-na-internet-google-cloud-run)
25. [Domínio próprio (tehillim.com.br)](#25-domínio-próprio-tehillimcombr)
26. [Versionamento e deploy automático (GitHub + CI/CD)](#26-versionamento-e-deploy-automático-github--cicd)

---

## 1. Pré-requisitos

Antes de começar, você precisa ter instalado na sua máquina:

### Python 3.10 ou superior

Verifique no terminal:
```
python3 --version
```
Se aparecer `Python 3.10.x` ou maior, está certo. Se não tiver, baixe em https://python.org/downloads

### Um editor de código

Recomendado: **VS Code** (https://code.visualstudio.com). Instale a extensão "Python" dentro do VS Code.

### Git (opcional mas recomendado)

Para controle de versão. Baixe em https://git-scm.com se ainda não tiver.

### Conta no Supabase

Gratuita. Será criada na próxima etapa.

---

## 2. Criar conta e projeto no Supabase

O Supabase é o serviço que vai guardar os dados dos alunos, gerenciar o login e armazenar as gravações de áudio.

### Passo a passo:

1. Acesse https://supabase.com e clique em **"Start your project"**
2. Crie uma conta gratuita (pode usar sua conta do GitHub)
3. Após logar, clique em **"New project"**
4. Preencha:
   - **Name:** tehillim (ou o nome que preferir)
   - **Database Password:** escolha uma senha forte e **anote ela** em lugar seguro
   - **Region:** escolha a mais próxima de você (ex.: South America - São Paulo)
5. Clique em **"Create new project"** e aguarde 1-2 minutos para o projeto ser criado

### Pegar as chaves de API:

Após criado o projeto:

1. No menu lateral esquerdo, clique em **"Project Settings"** (ícone de engrenagem)
2. Clique em **"API"**
3. Você vai ver três informações que precisa anotar:
   - **Project URL** — começa com `https://xxxxxxxxxxx.supabase.co`
   - **anon / public key** — uma chave longa começando com `eyJ...` — esta é pública e vai no HTML
   - **service_role / secret key** — outra chave longa — esta é **secreta**, nunca coloque no HTML

Anote as três em um lugar seguro. Você vai precisar delas no arquivo `.env`.

### Criar o bucket de armazenamento:

Este bucket vai guardar as gravações de áudio dos alunos.

1. No menu lateral, clique em **"Storage"**
2. Clique em **"New bucket"**
3. **Name:** `recordings`
4. **Public bucket:** deixe **DESLIGADO** (privado)
5. Clique em **"Create bucket"**

---

## 3. Estrutura de pastas

### Por que esta estrutura?

Projetos Flask escaláveis usam dois padrões fundamentais:

**1. Application Factory** — em vez de criar o app Flask no topo de um arquivo e importá-lo em todo lugar, você cria uma função `create_app()` que monta o app sob demanda. Isso facilita testes, múltiplos ambientes (dev/staging/prod) e evita importações circulares.

**2. Blueprints** — em vez de colocar todas as rotas em um único `server.py`, cada área da aplicação vira um módulo independente com suas próprias rotas. Assim, autenticação, módulos de estudo, painel admin e API ficam completamente separados. Adicionar ou remover uma área não afeta as outras.

A estrutura que vamos usar reflete esses dois padrões:

```
tehillim/                               ← pasta raiz do projeto
│
├── app.py                              ← ponto de entrada: chama create_app()
├── requirements.txt                    ← dependências Python
├── Dockerfile                          ← empacotamento para deploy
├── .dockerignore
├── .env                                ← suas chaves secretas (nunca no GitHub)
├── .gitignore
│
├── .github/
│   └── workflows/
│       ├── deploy-staging.yml          ← deploy automático para staging
│       └── deploy-prod.yml             ← deploy automático para produção
│
├── tehillim/                           ← pacote Python principal
│   ├── __init__.py                     ← create_app(): monta e registra tudo
│   ├── config.py                       ← lê o .env, define configurações
│   ├── extensions.py                   ← inicializa clientes externos (Supabase)
│   │
│   ├── auth/                           ← Blueprint: autenticação
│   │   ├── __init__.py                 ← registra o blueprint "auth"
│   │   └── routes.py                   ← /login, /logout
│   │
│   ├── modules/                        ← Blueprint: trilha de estudo
│   │   ├── __init__.py                 ← registra o blueprint "modules"
│   │   └── routes.py                   ← /, /grupos, /group, /module, /trilhas, /aulas
│   │
│   ├── admin/                          ← Blueprint: painel do professor e admin
│   │   ├── __init__.py                 ← registra o blueprint "admin"
│   │   └── routes.py                   ← /dashboard, /admin
│   │
│   ├── api/                            ← Blueprint: endpoints REST
│   │   ├── __init__.py                 ← registra o blueprint "api" com prefixo /api
│   │   └── routes.py                   ← /api/my-access, /api/modules, /api/progress...
│   │
│   ├── content/                        ← conteúdo dos módulos (dados puros, sem rotas)
│   │   ├── __init__.py                 ← expõe all_modules(), all_groups()
│   │   ├── types.py                    ← estruturas de dados (dataclasses)
│   │   ├── helpers.py                  ← funções para montar módulos
│   │   ├── groups.py                   ← definição dos grupos de módulos
│   │   └── modules/
│   │       ├── __init__.py             ← auto-descoberta de módulos
│   │       ├── m01_o_que_e_musica.py
│   │       └── (outros módulos...)
│   │
│   ├── static/
│   │   ├── bona/                       ← arquivos .musicxml do Método Bona
│   │   ├── css/
│   │   │   ├── styles.css
│   │   │   ├── games.css
│   │   │   ├── dashboard.css
│   │   │   └── admin.css
│   │   └── js/
│   │       ├── auth.js
│   │       ├── app.js
│   │       ├── audio.js
│   │       ├── vexflow-utils.js
│   │       ├── recorder.js
│   │       ├── games.js
│   │       ├── dashboard.js
│   │       ├── admin.js
│   │       └── group.js
│   │
│   └── templates/
│       ├── base.html                   ← layout mínimo (login, páginas simples)
│       ├── base_app.html               ← layout completo com sidebar
│       ├── auth/
│       │   └── login.html
│       ├── modules/                    ← páginas de estudo
│       │   ├── home.html
│       │   ├── grupos.html
│       │   ├── group.html
│       │   ├── trilhas.html
│       │   ├── module.html
│       │   ├── bona_module.html
│       │   └── bona_player.html
│       ├── pages/                      ← páginas gerais do aluno
│       │   ├── aulas.html
│       │   ├── desempenho.html
│       │   ├── conquistas.html
│       │   └── configuracoes.html
│       └── admin/                      ← páginas do professor/admin
│           ├── dashboard.html
│           └── admin.html
│
├── sql/
│   └── setup.sql                       ← script de criação do banco
│
└── docs/                               ← documentação do projeto
    ├── blueprint.md
    ├── ROADMAP.md
    └── CONTEUDOS.md
```

---

### Como os Blueprints se conectam

O arquivo `tehillim/__init__.py` é o ponto central que une tudo:

```python
from flask import Flask
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registra cada área da aplicação como um módulo independente
    from .auth    import bp as auth_bp
    from .modules import bp as modules_bp
    from .admin   import bp as admin_bp
    from .api     import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(modules_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
```

Cada Blueprint é declarado no seu próprio `__init__.py`. Por exemplo, `tehillim/auth/__init__.py`:

```python
from flask import Blueprint

bp = Blueprint("auth", __name__, template_folder="templates")

from . import routes  # importa as rotas após criar o blueprint
```

E `tehillim/auth/routes.py` contém apenas as rotas de autenticação:

```python
from flask import render_template, request, redirect
from . import bp

@bp.route("/login", methods=["GET", "POST"])
def login():
    return render_template("auth/login.html")

@bp.route("/logout")
def logout():
    # ...
    return redirect("/login")
```

Essa separação significa que, no futuro, você pode:
- Adicionar um novo Blueprint `payments/` sem tocar em nenhum arquivo existente
- Testar `auth/` isoladamente sem subir o resto da aplicação
- Ter desenvolvedores diferentes trabalhando em `admin/` e `modules/` sem conflitos

---

### Criar as pastas

No terminal, navegue até onde quer criar o projeto e execute:

```bash
mkdir tehillim
cd tehillim
mkdir -p tehillim/auth
mkdir -p tehillim/modules
mkdir -p tehillim/admin
mkdir -p tehillim/api
mkdir -p tehillim/content/modules
mkdir -p tehillim/static/bona
mkdir -p tehillim/static/css
mkdir -p tehillim/static/js
mkdir -p tehillim/templates/auth
mkdir -p tehillim/templates/modules
mkdir -p tehillim/templates/pages
mkdir -p tehillim/templates/admin
mkdir -p docs
mkdir -p .github/workflows
mkdir sql
```

Depois crie os arquivos `__init__.py` vazios (necessários para o Python reconhecer as pastas como módulos):

```bash
touch tehillim/__init__.py
touch tehillim/auth/__init__.py
touch tehillim/modules/__init__.py
touch tehillim/admin/__init__.py
touch tehillim/api/__init__.py
touch tehillim/content/__init__.py
touch tehillim/content/modules/__init__.py
```

---

## 4. Ambiente Python

### Criar ambiente virtual

Um ambiente virtual isola as dependências deste projeto para não misturar com outros projetos.

No terminal, dentro da pasta `growp`:

```bash
python3 -m venv .venv
```

Isso cria uma pasta oculta `.venv` com Python isolado.

### Ativar o ambiente virtual

**No Mac/Linux:**
```bash
source .venv/bin/activate
```

**No Windows:**
```bash
.venv\Scripts\activate
```

Você vai ver `(.venv)` aparecendo no início da linha do terminal. Isso confirma que está ativo.

> **Importante:** sempre que abrir um terminal novo para trabalhar no projeto, ative o ambiente virtual antes.

### Criar o arquivo requirements.txt

Crie o arquivo `tehillim/requirements.txt` com o seguinte conteúdo:

```
Flask>=3.0,<4.0
python-dotenv>=1.0
requests>=2.32
```

### Instalar as dependências

```bash
pip install -r requirements.txt
```

Aguarde o download e instalação. Quando terminar, confirme com:

```bash
pip list
```

Você deve ver Flask, python-dotenv e requests na lista.

### Criar o arquivo .env

Crie o arquivo `tehillim/.env` (sem extensão, só `.env`) com o seguinte conteúdo. **Substitua pelos seus valores reais do Supabase:**

```
SUPABASE_URL=https://xxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN...
```

> **Atenção:** este arquivo contém segredos. Nunca o envie para o GitHub. Se usar Git, crie um `.gitignore` com o conteúdo:
> ```
> .env
> .venv/
> __pycache__/
> *.py[cod]
> .DS_Store
> ```

---

## 5. Arquivo de configuração

A seção de configuração tem dois arquivos: `config.py` que lê o `.env`, e `extensions.py` que inicializa os clientes externos (Supabase) de forma centralizada.

### 5.1 — `tehillim/tehillim/config.py`

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", 8000))
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
```

**O que este arquivo faz:**
- `load_dotenv(...)` — lê o `.env` da raiz do projeto
- `Config` — classe com todas as configurações. O Flask lê essa classe com `app.config.from_object(Config)`. Cada variável vira um item acessível via `current_app.config["SUPABASE_URL"]` em qualquer Blueprint

### 5.2 — `tehillim/tehillim/extensions.py`

Este arquivo centraliza as funções de comunicação com o Supabase via HTTP. Todos os Blueprints importam daqui em vez de replicar o código.

```python
import requests
from flask import current_app


def sb_headers():
    """Cabeçalhos com a service key para chamadas administrativas ao Supabase."""
    key = current_app.config["SUPABASE_SERVICE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def sb_get(table: str, params: dict | None = None) -> list:
    """Faz GET na API REST do Supabase e retorna a lista de registros."""
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.get(url, headers=sb_headers(), params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_post(table: str, payload, prefer: str = "return=representation"):
    """Faz POST (inserção) na API REST do Supabase."""
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.post(url, headers={**sb_headers(), "Prefer": prefer}, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_put(path: str, payload: dict):
    """Faz PUT na API de administração do Supabase Auth."""
    url = f"{current_app.config['SUPABASE_URL']}{path}"
    r = requests.put(url, headers=sb_headers(), json=payload, timeout=10)
    r.raise_for_status()
    return r.json()


def sb_delete(table: str, params: dict):
    """Faz DELETE na API REST do Supabase."""
    url = f"{current_app.config['SUPABASE_URL']}/rest/v1/{table}"
    r = requests.delete(url, headers=sb_headers(), params=params, timeout=10)
    r.raise_for_status()


def get_user_from_token(token: str) -> dict | None:
    """Valida um Bearer token e retorna os dados do usuário, ou None se inválido."""
    url = f"{current_app.config['SUPABASE_URL']}/auth/v1/user"
    r = requests.get(
        url,
        headers={"Authorization": f"Bearer {token}", "apikey": current_app.config["SUPABASE_ANON_KEY"]},
        timeout=5,
    )
    return r.json() if r.ok else None
```

---

## 6. Ponto de entrada da aplicação

São dois arquivos: `tehillim/__init__.py` que monta o app Flask com todos os Blueprints, e `app.py` na raiz que você executa para iniciar o servidor.

### 6.1 — `tehillim/tehillim/__init__.py` (Application Factory)

```python
from flask import Flask
from .config import Config


def create_app(config=None) -> Flask:
    app = Flask(
        __name__,
        static_folder="static",
        static_url_path="/static",
        template_folder="templates",
    )
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    # Injeta URL e chave pública do Supabase em todos os templates via Jinja2
    @app.context_processor
    def inject_supabase():
        return {
            "supabase_url":      app.config["SUPABASE_URL"],
            "supabase_anon_key": app.config["SUPABASE_ANON_KEY"],
        }

    # Registra os Blueprints — cada um é uma área independente da aplicação
    from .auth    import bp as auth_bp
    from .modules import bp as modules_bp
    from .admin   import bp as admin_bp
    from .api     import bp as api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(modules_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
```

**O que este arquivo faz:**
- `create_app()` — função que monta e retorna o app Flask. É o padrão "Application Factory". Aceita um dicionário de configurações opcional, o que facilita testes.
- `app.config.from_object(Config)` — carrega todas as variáveis de `config.py`
- `@app.context_processor` — injeta variáveis Supabase automaticamente em todos os templates HTML, sem precisar passá-las manualmente em cada rota
- `app.register_blueprint(...)` — conecta cada módulo independente ao app principal. O `api_bp` recebe o prefixo `/api`, então todas as rotas dentro dele ficam em `/api/...`

### 6.2 — `tehillim/app.py`

```python
import os
from tehillim import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
```

**O que este arquivo faz:**
- É o arquivo que você executa para iniciar o servidor: `python app.py`
- `host="0.0.0.0"` — aceita conexões de qualquer origem, necessário para funcionar no Cloud Run
- `port=int(os.environ.get("PORT", 8000))` — usa a porta que o Cloud Run definir, ou 8000 localmente
- `debug=False` em produção — nunca use `debug=True` em produção

---

## 7. Sistema de conteúdo (módulos e grupos)

Esta é a parte que define TODO o conteúdo educacional da plataforma. O conteúdo fica em Python puro — sem banco de dados, sem CMS.

### 7.1 Tipos de dados — `content/types.py`

Crie `tehillim/tehillim/content/types.py`:

```python
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
```

**O que são `@dataclass(frozen=True)`?**
Dataclasses são uma forma mais simples de criar classes em Python. O parâmetro `frozen=True` as torna imutáveis — depois de criadas, não podem ser alteradas. São como registros de dados.

### 7.2 Funções auxiliares — `content/helpers.py`

Crie `tehillim/tehillim/content/helpers.py`:

```python
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
```

### 7.3 Auto-descoberta de módulos — `content/modules/__init__.py`

Crie `tehillim/tehillim/content/modules/__init__.py`:

```python
"""
Auto-descobre todos os arquivos .py desta pasta e monta a tupla MODULES.

Cada arquivo pode exportar:
  MODULE  — um único StudyModule
  MODULES — uma lista ou tupla de StudyModules

Todos são coletados, ordenados por number e expostos como MODULES.
"""
import importlib
import pkgutil
from pathlib import Path

from tehillim.content.types import StudyModule

_HERE = Path(__file__).parent


def _load_all() -> tuple[StudyModule, ...]:
    modules: list[StudyModule] = []
    for _, name, _ in pkgutil.iter_modules([str(_HERE)]):
        if name.startswith("_"):
            continue
        mod = importlib.import_module(f"tehillim.content.modules.{name}")
        if hasattr(mod, "MODULE"):
            sm = mod.MODULE
            if isinstance(sm, StudyModule):
                modules.append(sm)
        if hasattr(mod, "MODULES"):
            for sm in mod.MODULES:
                if isinstance(sm, StudyModule):
                    modules.append(sm)

    modules.sort(key=lambda m: m.number)
    return tuple(modules)


MODULES: tuple[StudyModule, ...] = _load_all()
```

**Como funciona:** quando Python importa este pacote, `_load_all()` varre todos os arquivos `.py` da pasta, importa cada um, procura por `MODULE` ou `MODULES`, coleta tudo e ordena por número. Isso significa que adicionar um novo módulo é tão simples quanto criar um novo arquivo `.py` na pasta.

### 7.4 Exemplo de módulo — `m01_o_que_e_musica.py`

Crie `tehillim/tehillim/content/modules/m01_o_que_e_musica.py`:

```python
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
```

**Estrutura de cada módulo:**
- `number` — número único do módulo (1, 2, 3... para regulares; 101-140 para Bona; 201-212 para Pozzoli)
- `slug` — identificador na URL, ex.: `"o-que-e-musica"` → `/modulos/o-que-e-musica`
- `title` — nome exibido
- `description` — frase curta descritiva
- `topics` — tupla de palavras-chave (3 a 5 itens)
- `theory` — texto explicativo do conteúdo
- `visual` — descrição do que o aluno vai ver na etapa visual
- `exercises` — tupla com 2 a 4 exercícios usando as fábricas `mc()`, `tf()`, `fill()`, `match()`
- `game` — texto da missão/jogo final
- `game_kind` — tipo do jogo (ver lista em `STEP_KINDS` no `helpers.py`)
- `video_url` — link do YouTube (opcional)

### 7.5 Grupos de módulos — `content/groups.py`

Crie `tehillim/tehillim/content/groups.py`:

```python
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
```

### 7.6 API pública do conteúdo — `content/__init__.py`

Crie `tehillim/tehillim/content/__init__.py`:

```python
"""API pública do pacote de conteúdo."""
from tehillim.content.groups import GROUPS
from tehillim.content.helpers import STEP_KINDS
from tehillim.content.modules import MODULES
from tehillim.content.types import Exercise, ModuleGroup, StudyModule, TrailStep


def get_module(slug: str) -> StudyModule | None:
    return next((m for m in MODULES if m.slug == slug), None)


def get_group(slug: str) -> ModuleGroup | None:
    return next((g for g in GROUPS if g.slug == slug), None)


def groups_payload() -> list[dict[str, object]]:
    return [g.to_payload() for g in GROUPS]


def groups_summary() -> list[dict[str, object]]:
    return [g.to_summary() for g in GROUPS]


def modules_payload() -> list[dict[str, object]]:
    return [m.to_payload() for m in MODULES]


def module_summaries() -> list[dict[str, object]]:
    return [m.to_summary() for m in MODULES]


__all__ = [
    "GROUPS", "MODULES", "STEP_KINDS",
    "Exercise", "ModuleGroup", "StudyModule", "TrailStep",
    "get_module", "get_group",
    "groups_payload", "groups_summary",
    "module_summaries", "modules_payload",
]
```

---

## 8. Rotas Flask (Blueprints)

Em vez de um único `server.py` com todas as rotas, cada área da aplicação tem seu próprio arquivo de rotas. Crie os quatro Blueprints abaixo.

---

### 8.1 — Blueprint de autenticação

**`tehillim/tehillim/auth/__init__.py`:**

```python
from flask import Blueprint

bp = Blueprint("auth", __name__, template_folder="../templates")

from . import routes  # noqa: E402, F401
```

**`tehillim/tehillim/auth/routes.py`:**

```python
from flask import render_template
from . import bp

@bp.get("/login")
def login():
    return render_template("auth/login.html")
```

---

### 8.2 — Blueprint de módulos (páginas do aluno)

**`tehillim/tehillim/modules/__init__.py`:**

```python
from flask import Blueprint

bp = Blueprint("modules", __name__, template_folder="../templates")

from . import routes  # noqa: E402, F401
```

**`tehillim/tehillim/modules/routes.py`:**

```python
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote

from flask import abort, current_app, render_template, request

from . import bp
from tehillim.content import get_group, get_module, groups_summary


def _groups():
    return groups_summary()


def _ta_cookie() -> tuple[set, bool]:
    """Lê o cookie 'ta' com slugs liberados e flag de professor."""
    try:
        raw  = request.cookies.get("ta", "")
        data = json.loads(unquote(raw)) if raw else {}
        return set(data.get("s", [])), bool(data.get("t", False))
    except Exception:
        return set(), False


@bp.get("/")
@bp.get("/index.html")
def index():
    return render_template("modules/home.html", groups=_groups(), active_page="inicio")


@bp.get("/grupos")
def grupos_page():
    return render_template("modules/grupos.html", groups=_groups(), active_page="grupos")


@bp.get("/grupos/<group_slug>")
def group_page(group_slug: str):
    selected_group = get_group(group_slug)
    if selected_group is None:
        abort(404)
    granted_slugs, is_teacher_cookie = _ta_cookie()
    return render_template(
        "modules/group.html",
        group=selected_group,
        granted_slugs=granted_slugs,
        is_teacher_cookie=is_teacher_cookie,
        active_page="grupos",
    )


@bp.get("/trilhas")
def trilhas_page():
    return render_template("modules/trilhas.html", groups=_groups(), active_page="trilhas")


@bp.get("/aulas")
def aulas_page():
    return render_template("pages/aulas.html", groups=_groups(), active_page="aulas")


@bp.get("/desempenho")
def desempenho_page():
    return render_template("pages/desempenho.html", groups=_groups(), active_page="desempenho")


@bp.get("/conquistas")
def conquistas_page():
    return render_template("pages/conquistas.html", groups=_groups(), active_page="conquistas")


@bp.get("/configuracoes")
def configuracoes_page():
    return render_template("pages/configuracoes.html", groups=_groups(), active_page="configuracoes")


_BONA_SHEETS = Path(__file__).resolve().parent.parent / "static" / "bona"


@bp.get("/modulos/<module_slug>")
def module_page(module_slug: str):
    selected_module = get_module(module_slug)
    if selected_module is None:
        abort(404)
    granted_slugs, is_teacher_cookie = _ta_cookie()
    access_ok = is_teacher_cookie or module_slug in granted_slugs
    if 101 <= selected_module.number <= 140:
        has_sheet = (_BONA_SHEETS / f"{module_slug}.musicxml").exists()
        return render_template(
            "modules/bona_module.html",
            module=selected_module,
            access_ok=access_ok,
            has_sheet=has_sheet,
            groups=_groups(),
        )
    return render_template(
        "modules/module.html",
        module=selected_module,
        access_ok=access_ok,
        groups=_groups(),
    )


@bp.get("/bona-player/<slug>")
def bona_player(slug: str):
    has_sheet = (_BONA_SHEETS / f"{slug}.musicxml").exists()
    return render_template("modules/bona_player.html", slug=slug, has_sheet=has_sheet)
```

---

### 8.3 — Blueprint de administração

**`tehillim/tehillim/admin/__init__.py`:**

```python
from flask import Blueprint

bp = Blueprint("admin", __name__, template_folder="../templates")

from . import routes  # noqa: E402, F401
```

**`tehillim/tehillim/admin/routes.py`:**

```python
from flask import render_template
from . import bp

@bp.get("/dashboard")
def dashboard():
    return render_template("admin/dashboard.html")

@bp.get("/admin")
def admin():
    return render_template("admin/admin.html")
```

---

### 8.4 — Blueprint de API

**`tehillim/tehillim/api/__init__.py`:**

```python
from flask import Blueprint

bp = Blueprint("api", __name__)

from . import routes  # noqa: E402, F401
```

**`tehillim/tehillim/api/routes.py`:**

```python
from __future__ import annotations

from flask import abort, current_app, jsonify, request
import requests as http

from . import bp
from tehillim.content import get_module, groups_summary, modules_payload
from tehillim.content.demo_games import DEMO_GAMES
from tehillim.extensions import (
    get_user_from_token, sb_delete, sb_get, sb_headers, sb_post, sb_put,
)


# ── Conteúdo público ──────────────────────────────────────────────────────────

@bp.get("/groups")
def group_list():
    return jsonify({"groups": groups_summary()})


@bp.get("/modules")
def modules():
    return jsonify({"modules": modules_payload()})


@bp.get("/modules/<module_slug>")
def module_content(module_slug: str):
    selected_module = get_module(module_slug)
    if selected_module is None:
        abort(404)
    return jsonify(selected_module.to_payload())


@bp.get("/games/demo")
def games_demo():
    return jsonify({"games": DEMO_GAMES})


@bp.get("/bona/<slug>")
def bona_sheet(slug: str):
    from pathlib import Path
    from flask import send_file
    sheet_path = Path(__file__).resolve().parent.parent / "static" / "bona" / f"{slug}.musicxml"
    if not sheet_path.exists():
        abort(404)
    return send_file(sheet_path, mimetype="application/xml")


# ── Acesso do aluno ───────────────────────────────────────────────────────────

@bp.get("/my-access")
def my_access():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"slugs": [], "isTeacher": False})

    user_data = get_user_from_token(auth_header[7:])
    if not user_data:
        return jsonify({"slugs": [], "isTeacher": False})

    user_id    = user_data.get("id")
    is_teacher = (user_data.get("user_metadata") or {}).get("role") == "teacher"

    if is_teacher:
        return jsonify({"slugs": [], "isTeacher": True})

    try:
        rows = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{user_id}"})
        return jsonify({"slugs": [r["module_slug"] for r in rows], "isTeacher": False})
    except Exception:
        return jsonify({"slugs": [], "isTeacher": False}), 500


# ── API Professor ─────────────────────────────────────────────────────────────

@bp.get("/teacher/students")
def teacher_students():
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.get(
        f"{supabase_url}/auth/v1/admin/users",
        headers=sb_headers(),
        params={"per_page": 200},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"users": []})

    from collections import defaultdict
    users_raw = r.json().get("users", [])
    users = {
        u["id"]: {
            "email": u["email"],
            "name":  (u.get("user_metadata") or {}).get("name") or "",
            "role":  (u.get("user_metadata") or {}).get("role") or "",
        }
        for u in users_raw
    }

    progress  = sb_get("module_progress", {"select": "user_id,module_slug,completed,updated_at", "order": "updated_at.desc"})
    study     = sb_get("study_days",      {"select": "user_id,day", "order": "day.desc"})
    prog_map  = defaultdict(list)
    study_map = defaultdict(list)

    for row in progress:
        prog_map[row["user_id"]].append(row)
    for row in study:
        study_map[row["user_id"]].append(row["day"])

    result = []
    for uid, info in users.items():
        result.append({
            "id": uid, "email": info["email"], "name": info["name"], "role": info["role"],
            "modules_completed": sum(1 for p in prog_map[uid] if p["completed"] > 0),
            "study_days":        len(study_map[uid]),
            "last_activity":     prog_map[uid][0]["updated_at"] if prog_map[uid] else None,
        })

    result.sort(key=lambda x: x["last_activity"] or "", reverse=True)
    return jsonify({"students": result})


@bp.get("/teacher/student/<user_id>/access")
def teacher_student_access(user_id: str):
    try:
        rows = sb_get("student_access", {"select": "module_slug", "user_id": f"eq.{user_id}"})
        return jsonify({"slugs": [r["module_slug"] for r in rows]})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.put("/teacher/student/<user_id>/access")
def teacher_sync_access(user_id: str):
    body  = request.get_json(silent=True) or {}
    slugs = [s.strip() for s in body.get("slugs", []) if s.strip()]
    supabase_url = current_app.config["SUPABASE_URL"]

    r = http.delete(
        f"{supabase_url}/rest/v1/student_access",
        headers=sb_headers(),
        params={"user_id": f"eq.{user_id}"},
        timeout=10,
    )
    if not r.ok:
        return jsonify({"error": r.text}), r.status_code

    if slugs:
        rows = [{"user_id": user_id, "module_slug": s} for s in slugs]
        r = http.post(
            f"{supabase_url}/rest/v1/student_access",
            headers={**sb_headers(), "Prefer": "return=minimal"},
            json=rows,
            timeout=10,
        )
        if not r.ok:
            return jsonify({"error": r.text}), r.status_code

    return jsonify({"slugs": slugs})


@bp.post("/teacher/comments")
def teacher_add_comment():
    body        = request.get_json(silent=True) or {}
    student_id  = body.get("student_id", "").strip()
    content     = body.get("content", "").strip()
    module_slug = body.get("module_slug") or None
    if not student_id or not content:
        abort(400)
    result = sb_post("teacher_comments", {"student_id": student_id, "content": content, "module_slug": module_slug})
    return jsonify(result[0]), 201


@bp.delete("/teacher/comments/<comment_id>")
def teacher_delete_comment(comment_id: str):
    sb_delete("teacher_comments", {"id": f"eq.{comment_id}"})
    return "", 204


@bp.get("/teacher/student/<user_id>")
def teacher_student_detail(user_id: str):
    progress = sb_get("module_progress",  {"select": "module_slug,completed,updated_at", "user_id": f"eq.{user_id}", "order": "updated_at.desc"})
    study    = sb_get("study_days",       {"select": "day",                              "user_id": f"eq.{user_id}", "order": "day.desc"})
    comments = sb_get("teacher_comments", {"select": "id,module_slug,content,created_at","student_id": f"eq.{user_id}", "order": "created_at.desc"})
    return jsonify({"progress": progress, "study_days": [r["day"] for r in study], "comments": comments})


# ── API Admin ─────────────────────────────────────────────────────────────────

@bp.post("/admin/create-user")
def admin_create_user():
    body     = request.get_json(silent=True) or {}
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "").strip()
    name     = body.get("name", "").strip()
    if not email or not password:
        abort(400)
    payload: dict = {"email": email, "password": password, "email_confirm": True}
    if name:
        payload["user_metadata"] = {"name": name}
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.post(f"{supabase_url}/auth/v1/admin/users", headers=sb_headers(), json=payload, timeout=10)
    if not r.ok:
        return jsonify({"error": r.json().get("msg", r.text)}), r.status_code
    return jsonify({"user": r.json()}), 201


@bp.post("/admin/reset-password")
def admin_reset_password():
    body     = request.get_json(silent=True) or {}
    user_id  = body.get("user_id", "").strip()
    password = body.get("password", "").strip()
    if not user_id or not password:
        abort(400)
    result = sb_put(f"/auth/v1/admin/users/{user_id}", {"password": password})
    return jsonify({"ok": True})


@bp.post("/admin/set-teacher/<user_id>")
def admin_set_teacher(user_id: str):
    sb_put(f"/auth/v1/admin/users/{user_id}", {"user_metadata": {"role": "teacher"}})
    return jsonify({"ok": True})


@bp.delete("/admin/delete-user/<user_id>")
def admin_delete_user(user_id: str):
    supabase_url = current_app.config["SUPABASE_URL"]
    r = http.delete(f"{supabase_url}/auth/v1/admin/users/{user_id}", headers=sb_headers(), timeout=10)
    if not r.ok:
        return jsonify({"error": r.text}), r.status_code
    return "", 204
```

---

**Crie o arquivo `tehillim/tehillim/content/demo_games.py`** (pode começar vazio):

```python
DEMO_GAMES = []
```

---

## 8.5 — Controle de acesso: páginas exclusivas do professor

Algumas páginas — o dashboard do professor e o painel admin — só devem ser acessíveis por quem tem o papel `teacher`. Esta seção explica como funciona esse controle em duas camadas: no servidor (Python) e no navegador (JavaScript).

---

### Como o papel de professor é armazenado

O papel é salvo nos metadados do usuário dentro do Supabase Auth. Quando você marca alguém como professor pelo painel admin, o Supabase registra:

```json
{ "user_metadata": { "role": "teacher" } }
```

Quando o aluno faz login, o `auth.js` chama `/api/my-access`, que lê esse campo e responde `"isTeacher": true`. O JavaScript então grava um cookie chamado `ta` com esse valor:

```
ta = {"s": ["slug1", "slug2"], "t": true}
```

O `t: true` significa professor. O servidor lê esse cookie em cada requisição para decidir se libera ou bloqueia a página.

---

### Camada 1 — Proteção no servidor (Python)

Crie um helper em `tehillim/tehillim/extensions.py` para verificar o cookie `ta`:

```python
import json
from urllib.parse import unquote
from flask import request, redirect


def is_teacher_request() -> bool:
    """Retorna True se o cookie 'ta' indica que o usuário é professor."""
    try:
        raw  = request.cookies.get("ta", "")
        data = json.loads(unquote(raw)) if raw else {}
        return bool(data.get("t", False))
    except Exception:
        return False


def require_teacher():
    """
    Use no início de uma rota para bloquear acesso de não-professores.
    Redireciona para '/' se o usuário não for professor.
    Exemplo de uso:
        @bp.get("/dashboard")
        def dashboard():
            if err := require_teacher(): return err
            return render_template("admin/dashboard.html")
    """
    if not is_teacher_request():
        return redirect("/")
    return None
```

Com isso, proteger qualquer rota é uma linha de código. Atualize `tehillim/tehillim/admin/routes.py`:

```python
from flask import render_template, redirect
from . import bp
from tehillim.extensions import require_teacher


@bp.get("/dashboard")
def dashboard():
    if err := require_teacher(): return err
    return render_template("admin/dashboard.html")


@bp.get("/admin")
def admin():
    if err := require_teacher(): return err
    return render_template("admin/admin.html")
```

Se um aluno tentar acessar `/dashboard` diretamente pela URL, o servidor detecta que o cookie não tem `t: true` e redireciona para a página inicial — sem mostrar nada da página.

> **Importante:** o cookie `ta` é definido pelo JavaScript após o login. Enquanto o usuário não fizer login, o cookie não existe, e `is_teacher_request()` retorna `False`. Isso significa que páginas protegidas também ficam inacessíveis para usuários deslogados — o que é o comportamento correto.

---

### Camada 2 — Proteção nas APIs (Python)

As rotas de API do professor (como `/api/teacher/students`) também precisam ser protegidas. A diferença é que APIs recebem um Bearer token no cabeçalho, não um cookie. Adicione um helper em `extensions.py`:

```python
from flask import request, jsonify


def require_teacher_token():
    """
    Versão para APIs: valida o Bearer token e verifica se o usuário é professor.
    Retorna uma resposta 403 se não for professor, ou None se passar.
    Exemplo de uso:
        @bp.get("/teacher/students")
        def teacher_students():
            if err := require_teacher_token(): return err
            ...
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "Não autorizado"}), 403

    user_data = get_user_from_token(auth_header[7:])
    if not user_data:
        return jsonify({"error": "Token inválido"}), 403

    is_teacher = (user_data.get("user_metadata") or {}).get("role") == "teacher"
    if not is_teacher:
        return jsonify({"error": "Acesso restrito ao professor"}), 403

    return None
```

Use em `tehillim/tehillim/api/routes.py` nas rotas sensíveis:

```python
@bp.get("/teacher/students")
def teacher_students():
    if err := require_teacher_token(): return err
    # ... resto do código
```

---

### Camada 3 — Proteção no navegador (JavaScript)

Mesmo com o servidor bloqueando, é importante esconder os links e menus do professor na interface. No template `base_app.html`, o link para o dashboard só aparece se o usuário for professor:

```html
<!-- No sidebar, dentro do {% block nav %} -->
<script>
  window.auth.ready.then(async () => {
    const { isTeacher } = await window.auth.getAccess();
    if (isTeacher) {
      document.getElementById("nav-dashboard").style.display = "";
      document.getElementById("nav-admin").style.display = "";
    }
  });
</script>

<!-- Os links ficam ocultos por padrão -->
<a id="nav-dashboard" href="/dashboard" style="display:none">Dashboard</a>
<a id="nav-admin"     href="/admin"     style="display:none">Admin</a>
```

Dessa forma, alunos não veem os links e professores os veem após o carregamento.

---

### Como adicionar uma nova página exclusiva do professor

Sempre que precisar criar uma nova página restrita ao professor, siga este checklist:

1. **Crie a rota em `admin/routes.py`** com `if err := require_teacher(): return err` na primeira linha.
2. **Crie o template HTML** em `tehillim/tehillim/templates/admin/`.
3. **Adicione o link na sidebar** do `base_app.html` com `style="display:none"` e um `id` único.
4. **Mostre o link** no JavaScript da sidebar condicionado a `isTeacher`.
5. **Teste acessando a URL diretamente sem estar logado como professor** — deve redirecionar para `/`.

---

### Referência: onde cada URL fica mapeada

| URL | Acesso | Blueprint | Arquivo |
|-----|--------|-----------|---------|
| `/login` | público | auth | `auth/routes.py` |
| `/` | aluno | modules | `modules/routes.py` |
| `/grupos`, `/grupos/<slug>` | aluno | modules | `modules/routes.py` |
| `/trilhas`, `/aulas` | aluno | modules | `modules/routes.py` |
| `/desempenho`, `/conquistas`, `/configuracoes` | aluno | modules | `modules/routes.py` |
| `/modulos/<slug>` | aluno (com acesso liberado) | modules | `modules/routes.py` |
| `/bona-player/<slug>` | aluno (com acesso liberado) | modules | `modules/routes.py` |
| `/dashboard` | **professor** | admin | `admin/routes.py` |
| `/admin` | **professor** | admin | `admin/routes.py` |
| `/api/groups`, `/api/modules` | público | api | `api/routes.py` |
| `/api/my-access` | aluno logado | api | `api/routes.py` |
| `/api/teacher/...` | **professor** | api | `api/routes.py` |
| `/api/admin/...` | **professor** | api | `api/routes.py` |

---

## 9. Banco de dados no Supabase

Agora vamos criar as tabelas no Supabase.

### Passo a passo:

1. Acesse seu projeto no Supabase (https://supabase.com)
2. No menu lateral, clique em **"SQL Editor"**
3. Clique em **"New query"**
4. Cole o conteúdo abaixo e clique em **"Run"** (ou pressione Ctrl+Enter)

```sql
-- ── Progresso dos módulos ─────────────────────────────────────────────────────
create table if not exists module_progress (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  completed   int  not null default 0,
  updated_at  timestamptz default now(),
  unique (user_id, module_slug)
);

-- ── Dias de estudo ────────────────────────────────────────────────────────────
create table if not exists study_days (
  user_id uuid references auth.users(id) on delete cascade,
  day     date not null,
  primary key (user_id, day)
);

-- ── Tentativas de jogos ───────────────────────────────────────────────────────
create table if not exists game_attempts (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text,
  game_kind   text,
  score       numeric,
  created_at  timestamptz default now()
);

-- ── Ativar RLS (Row Level Security) nas tabelas acima ─────────────────────────
-- RLS garante que cada aluno só veja seus próprios dados
alter table module_progress enable row level security;
alter table study_days      enable row level security;
alter table game_attempts   enable row level security;

create policy "own data" on module_progress for all using (auth.uid() = user_id);
create policy "own data" on study_days      for all using (auth.uid() = user_id);
create policy "own data" on game_attempts   for all using (auth.uid() = user_id);

-- ── Gravações de áudio ────────────────────────────────────────────────────────
create table if not exists submissions (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  audio_path  text not null,
  status      text not null default 'pending',
  created_at  timestamptz default now()
);

alter table submissions enable row level security;
create policy "own data" on submissions for all using (auth.uid() = user_id);

-- ── Controle de acesso (professor libera módulos para alunos) ─────────────────
create table if not exists student_access (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  granted_at  timestamptz default now(),
  unique (user_id, module_slug)
);

alter table student_access enable row level security;
-- Aluno pode VER quais módulos tem acesso; professor usa service_role (bypassa RLS)
create policy "read own access" on student_access
  for select to authenticated
  using (auth.uid() = user_id);

-- ── Respostas de quiz ─────────────────────────────────────────────────────────
create table if not exists quiz_answers (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references auth.users(id) on delete cascade,
  module_slug text not null,
  step_index  int  not null,
  step_kind   text not null,
  question    text,
  answer      text,
  correct     boolean,
  created_at  timestamptz default now()
);

alter table quiz_answers enable row level security;
create policy "own data" on quiz_answers for all using (auth.uid() = user_id);

-- ── Comentários do professor ──────────────────────────────────────────────────
create table if not exists teacher_comments (
  id          uuid primary key default gen_random_uuid(),
  student_id  uuid references auth.users(id) on delete cascade,
  module_slug text,
  content     text not null,
  created_at  timestamptz default now()
);

alter table teacher_comments enable row level security;
create policy "read own comments" on teacher_comments
  for select to authenticated
  using (auth.uid() = student_id);
```

Aguarde a mensagem "Success" aparecer.

### Políticas de armazenamento de áudio:

Ainda no SQL Editor, rode mais este bloco **depois** de ter criado o bucket `recordings` (etapa 2):

```sql
-- Aluno pode enviar gravações para a pasta com seu próprio user_id
create policy "upload own recordings" on storage.objects
  for insert to authenticated
  with check (
    bucket_id = 'recordings'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Aluno pode ler suas próprias gravações
create policy "read own recordings" on storage.objects
  for select to authenticated
  using (
    bucket_id = 'recordings'
    and (storage.foldername(name))[1] = auth.uid()::text
  );
```

### Habilitar autenticação por e-mail:

1. No menu lateral do Supabase, clique em **"Authentication"**
2. Clique em **"Providers"**
3. Certifique-se de que **"Email"** está habilitado
4. Desative **"Confirm email"** se quiser que os usuários possam logar sem confirmar e-mail (recomendado para testes)

---

## 10. Templates base HTML

Os templates HTML usam Jinja2 (sistema de templates embutido no Flask). Variáveis do Python ficam entre `{{ }}` e blocos de controle entre `{% %}`.

### 10.1 Base mínima — `base.html`

Usado por páginas standalone (login, dashboard antigo). Crie `tehillim/tehillim/templates/base.html`:

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}tehillim{% endblock %}</title>
  <link rel="stylesheet" href="/static/css/styles.css">
  {% block head %}{% endblock %}
</head>
<body>
  {% block body %}{% endblock %}

  <script>
    window.SUPABASE_URL      = "{{ supabase_url }}";
    window.SUPABASE_ANON_KEY = "{{ supabase_anon_key }}";
  </script>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js"></script>
  <script src="/static/js/auth.js"></script>
  {% block scripts %}{% endblock %}
</body>
</html>
```

### 10.2 Base do aplicativo — `base_app.html`

Este é o template principal. Todas as páginas do app o estendem. Crie `tehillim/tehillim/templates/base_app.html`:

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Tehillim{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
    ::-webkit-scrollbar { display: none; }
    * { -ms-overflow-style: none; scrollbar-width: none; }
  </style>
  {% block head %}{% endblock %}
</head>
<body class="bg-[#FAF7F2] h-screen flex overflow-hidden text-gray-800">

  <!-- ══════════════ SIDEBAR ══════════════ -->
  <aside class="w-[210px] bg-white flex flex-col shadow-sm flex-shrink-0 overflow-y-auto">

    <!-- Logo -->
    <div class="flex flex-col items-center pt-7 pb-5 px-4">
      <a href="/" class="w-[58px] h-[58px] rounded-full border-[2.5px] border-gray-800 flex items-center justify-center">
        <span style="font-size:34px;font-family:'Georgia',serif;color:#1f2937;line-height:1;">&#119070;</span>
      </a>
      <p class="font-bold text-[11px] tracking-[3px] mt-2 text-gray-800">TEHILLIM</p>
      <p class="text-[9px] tracking-[2.5px] text-gray-400 uppercase">Orquestra</p>
    </div>

    <!-- Navegação -->
    <nav class="flex flex-col px-3 gap-0.5 flex-1">

      <a href="/" class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] transition-colors
        {% if active_page == 'inicio' %}bg-[#F2EAD8] text-[#7A5C2E] font-semibold{% else %}text-gray-500 hover:bg-gray-50{% endif %}">
        <svg class="w-4 h-4 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
          <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z"/>
        </svg>
        Início
      </a>

      <a href="/grupos" class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] transition-colors
        {% if active_page == 'grupos' %}bg-[#F2EAD8] text-[#7A5C2E] font-semibold{% else %}text-gray-500 hover:bg-gray-50{% endif %}">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z"/>
        </svg>
        Grupos
      </a>

      <a href="/trilhas" class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] transition-colors
        {% if active_page == 'trilhas' %}bg-[#F2EAD8] text-[#7A5C2E] font-semibold{% else %}text-gray-500 hover:bg-gray-50{% endif %}">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0118 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/>
        </svg>
        Minhas Trilhas
      </a>

      <a href="/aulas" class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] transition-colors
        {% if active_page == 'aulas' %}bg-[#F2EAD8] text-[#7A5C2E] font-semibold{% else %}text-gray-500 hover:bg-gray-50{% endif %}">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z"/>
        </svg>
        Aulas complementares
      </a>

      <a href="/desempenho" class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] transition-colors
        {% if active_page == 'desempenho' %}bg-[#F2EAD8] text-[#7A5C2E] font-semibold{% else %}text-gray-500 hover:bg-gray-50{% endif %}">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/>
        </svg>
        Desempenho
      </a>

      <a href="/conquistas" class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] transition-colors
        {% if active_page == 'conquistas' %}bg-[#F2EAD8] text-[#7A5C2E] font-semibold{% else %}text-gray-500 hover:bg-gray-50{% endif %}">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 013 3h-15a3 3 0 013-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 01-.982-3.172M9.497 14.25a7.454 7.454 0 00.981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 007.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 002.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 012.916.52 6.003 6.003 0 01-5.395 4.972m0 0a6.726 6.726 0 01-2.749 1.35m0 0a6.772 6.772 0 01-3.044 0"/>
        </svg>
        Conquistas
      </a>

      <a href="/configuracoes" class="flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] transition-colors
        {% if active_page == 'configuracoes' %}bg-[#F2EAD8] text-[#7A5C2E] font-semibold{% else %}text-gray-500 hover:bg-gray-50{% endif %}">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.6">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
        </svg>
        Configurações
      </a>
    </nav>

    <!-- Card motivacional -->
    <div class="mx-3 mb-5 mt-3">
      <div class="bg-[#F2EAD8] rounded-2xl p-4">
        <div class="flex items-center gap-2 mb-2">
          <div class="w-6 h-6 rounded-full bg-[#C4943A]/20 flex items-center justify-center text-xs">⭐</div>
          <p class="font-semibold text-xs text-gray-700">Continue aprendendo!</p>
        </div>
        <p class="text-[11px] text-gray-500 leading-relaxed mb-3">Você está no caminho certo para alcançar seus objetivos musicais.</p>
        <div class="flex items-center gap-2">
          <div class="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
            <div class="h-full bg-[#C4943A] rounded-full transition-all duration-500" id="sidebar-progress-bar" style="width:0%"></div>
          </div>
          <span class="text-[11px] font-semibold text-gray-600" id="sidebar-progress-pct">—</span>
        </div>
      </div>
    </div>
  </aside>

  <!-- ══════════════ ÁREA PRINCIPAL ══════════════ -->
  <div class="flex-1 flex flex-col overflow-hidden">
    {% block header %}{% endblock %}
    <div class="flex-1 overflow-y-auto">
      {% block content %}{% endblock %}
    </div>
  </div>

  <!-- Configuração do Supabase -->
  <script>
    window.SUPABASE_URL      = "{{ supabase_url }}";
    window.SUPABASE_ANON_KEY = "{{ supabase_anon_key }}";
  </script>
  <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/dist/umd/supabase.js"></script>
  <script src="/static/js/auth.js"></script>

  <!-- ① Leitura SÍNCRONA do localStorage — roda antes do DOMContentLoaded
       Garante que window._progress já existe quando as páginas renderizam -->
  <script>
    (function () {
      try {
        const total = {{ groups | sum(attribute='module_count') }};
        const prog  = [];
        let done    = 0;
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (!key?.startsWith('tehillim:') || !key.endsWith(':completed')) continue;
          const slug      = key.split(':')[1];
          const completed = Number(localStorage.getItem(key) || 0);
          prog.push({ module_slug: slug, completed });
          if (completed > 0) done++;
        }
        window._progress     = prog;
        window._doneModules  = done;
        window._totalModules = total;
        window._studyDays    = [];
        const sc = JSON.parse(localStorage.getItem('tehillim:streak') || 'null');
        window._streak = (sc?.value ?? 0);
      } catch (e) {}
    })();
  </script>

  <!-- ② Atualização assíncrona após auth concluir -->
  <script>
    function _computeStreak(days) {
      if (!days.length) return 0;
      const dates = days.map(d => d.day).sort().reverse();
      const today = new Date().toISOString().slice(0, 10);
      let streak = 0, cur = today;
      for (const d of dates) {
        if (d === cur) { streak++; const dt = new Date(cur); dt.setDate(dt.getDate() - 1); cur = dt.toISOString().slice(0, 10); }
        else if (d < cur) break;
      }
      return streak;
    }

    (async () => {
      try {
        await window.auth.ready;
        if (!window.auth.isLoggedIn()) return;

        const session    = window.auth.session;
        window._sb       = window.auth.client;
        window._userId   = session.user.id;
        window._userName = window.auth.getName();

        document.querySelectorAll('[data-user-name]').forEach(el => el.textContent = window._userName);

        const total = {{ groups | sum(attribute='module_count') }};
        const prog  = [];
        let done    = 0;
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          if (!key?.startsWith('tehillim:') || !key.endsWith(':completed')) continue;
          const slug      = key.split(':')[1];
          const completed = Number(localStorage.getItem(key) || 0);
          prog.push({ module_slug: slug, completed });
          if (completed > 0) done++;
        }
        const pct = total > 0 ? Math.round((done / total) * 100) : 0;
        const bar = document.getElementById('sidebar-progress-bar');
        const lbl = document.getElementById('sidebar-progress-pct');
        if (bar) bar.style.width = pct + '%';
        if (lbl) lbl.textContent = pct + '%';
        window._progress     = prog;
        window._totalModules = total;
        window._doneModules  = done;

        const today = new Date().toISOString().slice(0, 10);
        let sc = null;
        try { sc = JSON.parse(localStorage.getItem('tehillim:streak') || 'null'); } catch {}

        if (sc?.date === today) {
          window._streak = sc.value;
          document.querySelectorAll('[data-streak]').forEach(el => el.textContent = sc.value);
          return;
        }

        window.auth.client
          .from('study_days').select('day')
          .eq('user_id', session.user.id).order('day', { ascending: false })
          .then(({ data: days }) => {
            window._studyDays = days || [];
            window._streak    = _computeStreak(days || []);
            document.querySelectorAll('[data-streak]').forEach(el => el.textContent = window._streak);
            localStorage.setItem('tehillim:streak', JSON.stringify({ date: today, value: window._streak }));
          }).catch(() => {});

      } catch (e) { console.warn('sidebar init', e); }
    })();
  </script>

  {% block scripts %}{% endblock %}
</body>
</html>
```

---

## 11. JavaScript: autenticação (auth.js)

Este arquivo gerencia todo o sistema de login. Ele cria um objeto global `window.auth` acessível em todas as páginas.

Crie `tehillim/tehillim/static/js/auth.js`. O arquivo completo implementa:

**Funcionalidades principais:**
- `auth.init()` — inicializa o cliente Supabase, verifica sessão existente, sincroniza progresso
- `auth.signInWithPassword(email, password)` — login com e-mail e senha
- `auth.sendMagicLink(email)` — envia link mágico por e-mail
- `auth.signOut()` — faz logout, limpa cache
- `auth.getAccess()` — retorna `{ slugs: Set, isTeacher: bool }` usando cache em 3 camadas:
  1. Memória (60 segundos)
  2. `localStorage` (5 minutos)
  3. Servidor `/api/my-access` (quando cache expirar)
- `auth.saveProgress(slug, completed)` — salva progresso de um módulo no Supabase
- `auth.markStudyDay()` — registra o dia de estudo atual
- `auth._syncFromCloud()` — baixa progresso da nuvem e mescla com localStorage (máximo vence). Cache de 5 minutos para não fazer fetch toda navegação
- `auth._fetchAccess()` — busca slugs liberados do servidor e salva cookie `ta` para uso do Flask

**Convenção de chaves no localStorage:**
- `tehillim:<slug>:completed` — número de etapas concluídas por módulo
- `tehillim:access` — cache de acesso `{slugs, isTeacher, at}`
- `tehillim:last-sync` — timestamp da última sincronização com a nuvem
- `tehillim:streak` — cache do streak `{date, value}`

> O código completo do `auth.js` está no arquivo original do projeto em `tehillim/tehillim/static/js/auth.js`. Copie-o integralmente para o novo projeto.

---

## 12. JavaScript: trilha de estudo (app.js)

Gerencia a página de módulo (`/modulos/<slug>`). Lida com toda a lógica de progresso, renderização de exercícios e controle de acesso.

**Funcionamento geral:**
1. Lê `document.body.dataset.moduleSlug` para saber qual módulo carregar
2. Faz `GET /api/modules/<slug>` para obter os dados completos
3. Lê o progresso do `localStorage` (`tehillim:<slug>:completed`)
4. Renderiza a trilha lateral (`#study-path`) com os nós de progresso
5. Renderiza a etapa atual (`#study-stage`) com o conteúdo correto
6. Ao clicar "Concluir etapa": incrementa o progresso, salva no localStorage e no Supabase, libera a próxima etapa

**IDs HTML que o app.js espera encontrar:**
- `#study-path` — nav lateral com os botões de etapa
- `#stage-kind` — tipo da etapa (ex.: "Teoria")
- `#stage-title` — título da etapa
- `#stage-summary` — resumo
- `#stage-body` — corpo do texto
- `#stage-activity` — área de exercício/jogo
- `#stage-feedback` — mensagem de acerto/erro
- `#complete-step` — botão "Concluir etapa"
- `#reset-module` — botão "Reiniciar módulo"
- `#progress-label` — "X de Y"
- `#progress-bar` — barra de progresso (elemento com `style.width`)

> O código completo está em `tehillim/tehillim/static/js/app.js`. Copie integralmente.

---

## 13. JavaScript: áudio (audio.js)

Usa a Web Audio API do navegador para tocar notas musicais sem precisar de arquivos de som.

**Expõe `window.audio` com os métodos:**
- `audio.playNote(name)` — toca uma nota (aceita nomes em português: "Dó", "Ré", "Mi"... ou inglês: "C", "D", "E"...)
- `audio.playScale(names)` — toca uma sequência de notas
- `audio.playRhythm(pattern, bpm)` — toca um ritmo (array de 1s e 0s)
- `audio.correct()` — som de acerto
- `audio.wrong()` — som de erro
- `audio.tick()` — clique de metrônomo

> Copie o código completo de `tehillim/tehillim/static/js/audio.js`.

---

## 14. JavaScript: partituras (vexflow-utils.js)

Wrapper sobre a biblioteca VexFlow para renderizar partituras musicais em um elemento `<canvas>` ou `<div>`.

**Expõe `window.VFUtils` com os métodos:**
- `VFUtils.renderBlank(id, { timeSig })` — pentagrama vazio com clave e compasso
- `VFUtils.renderKeys(id, keys)` — notas como seminimas no pentagrama
- `VFUtils.renderRhythm(id, pattern)` — padrão rítmico (array de 1s e 0s)
- `VFUtils.renderFigureShowcase(id, figures)` — várias figuras rítmicas lado a lado

> Copie o código completo de `tehillim/tehillim/static/js/vexflow-utils.js`.

---

## 15. JavaScript: gravações (recorder.js)

Permite que alunos gravem áudio pelo microfone e enviem para o Supabase Storage.

**Expõe `window.recorder` com os métodos:**
- `recorder.start()` — solicita permissão de microfone e inicia gravação
- `recorder.stop()` — para a gravação, retorna um `Blob`
- `recorder.upload(blob, moduleSlug)` — envia para Storage e registra na tabela `submissions`
- `recorder.createWidget(moduleSlug)` — retorna um elemento HTML com botões de Gravar/Parar/Enviar

> Copie o código completo de `tehillim/tehillim/static/js/recorder.js`.

---

## 16. Páginas principais (templates)

Cada página estende `base_app.html` e define três blocos:
- `{% block title %}` — título da aba do navegador
- `{% block header %}` — barra superior âmbar com título e avatar
- `{% block content %}` — conteúdo principal da página
- `{% block scripts %}` — JavaScript específico da página

### Padrão do header em cada página

Todas as páginas do app têm um header com fundo âmbar (`#F2EAD8`) seguindo este padrão:

```html
{% block header %}
<header class="bg-[#F2EAD8] px-8 py-5 relative overflow-hidden flex-shrink-0">
  <div class="flex items-center justify-between relative z-10">
    <div>
      <p class="text-[12px] text-gray-500 uppercase tracking-wider font-medium">Subtítulo</p>
      <h1 class="text-[22px] font-bold text-gray-800 mt-0.5">Título da Página</h1>
    </div>
    <div class="flex items-center gap-4">
      <!-- Streak -->
      <div class="flex items-center gap-2">
        <span class="text-xl">🔥</span>
        <div class="leading-tight">
          <p class="font-bold text-[18px] text-gray-800 leading-none" data-streak>—</p>
          <p class="text-[10px] text-gray-500">dias de sequência</p>
        </div>
      </div>
      <div class="w-px h-7 bg-[#D4C4A8]"></div>
      <!-- Avatar → Configurações -->
      <a href="/configuracoes" class="flex items-center gap-1.5 cursor-pointer">
        <div class="w-9 h-9 rounded-full overflow-hidden">
          <svg viewBox="0 0 36 36" class="w-full h-full">
            <rect width="36" height="36" fill="#D4A574"/>
            <circle cx="18" cy="14" r="7" fill="#C49060"/>
            <ellipse cx="18" cy="32" rx="11" ry="8" fill="#C49060"/>
          </svg>
        </div>
        <svg class="w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
        </svg>
      </a>
    </div>
  </div>
  <!-- Decoração de fundo -->
  <div class="absolute right-[-20px] bottom-[-20px] text-[#C4943A] opacity-[0.08] select-none pointer-events-none"
       style="font-size:160px;line-height:1;font-family:'Georgia',serif;">&#119070;</div>
</header>
{% endblock %}
```

### Padrão dos scripts em páginas com conteúdo dinâmico

Páginas que exibem progresso do aluno usam este padrão para renderizar imediatamente (sem espera):

```javascript
{% block scripts %}
<script>
const GROUPS_DATA = {{ groups | tojson }};

document.addEventListener('DOMContentLoaded', () => {
  // window._progress já está definido (lido do localStorage de forma síncrona
  // pelo script no base_app.html antes mesmo do DOMContentLoaded)
  renderAll();
  
  // Atualiza novamente quando auth terminar (dados potencialmente mais frescos)
  window.auth.ready.then(() => {
    if (window._progress !== undefined) renderAll();
  });
});

function renderAll() {
  const prog    = window._progress || [];
  const done    = window._doneModules || 0;
  const total   = window._totalModules || 1;
  const streak  = window._streak || 0;
  const doneSet = new Set(prog.filter(p => p.completed > 0).map(p => p.module_slug));
  // ... sua lógica de renderização aqui
}
</script>
{% endblock %}
```

> As páginas completas (`home.html`, `grupos.html`, `group.html`, `trilhas.html`, `aulas.html`, `desempenho.html`, `conquistas.html`, `configuracoes.html`, `perfil.html`, `module.html`, `bona_module.html`, `bona_player.html`, `login.html`, `dashboard.html`, `admin.html`, `games_lab.html`) devem ser copiadas integralmente do projeto original, pois contêm lógica JavaScript extensa e markup HTML detalhado.

---

## 17. CSS: estilos globais

### `styles.css`

Usado pelas páginas antigas (base.html). Define o sistema de cores com variáveis CSS:

```css
:root {
  --ink:    #24313f;
  --mint:   #dff7ea;
  --sky:    #dcefff;
  --sun:    #ffd66b;
  --coral:  #ff8a7a;
  --plum:   #6d5dfc;
  --green:  #2e9f65;
  --shadow: 0 18px 48px rgba(31, 43, 56, .14);
  --radius: 8px;
}
```

> Copie o arquivo completo de `tehillim/tehillim/static/css/styles.css`.

### `games.css`

Estilos específicos para o laboratório de jogos e a área de estudo dos módulos.

> Copie de `tehillim/tehillim/static/css/games.css`.

### `dashboard.css` e `admin.css`

Estilos para o dashboard do professor e painel admin.

> Copie ambos de `tehillim/tehillim/static/css/`.

---

## 18. Primeiro teste: rodar localmente

Neste ponto você já tem o suficiente para testar se o servidor sobe corretamente.

### Verificar estrutura mínima

Antes de rodar, verifique que estes arquivos existem:
- `tehillim/app.py`
- `tehillim/.env` (com as chaves Supabase)
- `tehillim/requirements.txt`
- `tehillim/tehillim/__init__.py` (com `create_app()`)
- `tehillim/tehillim/config.py`
- `tehillim/tehillim/extensions.py`
- `tehillim/tehillim/auth/__init__.py` e `auth/routes.py`
- `tehillim/tehillim/modules/__init__.py` e `modules/routes.py`
- `tehillim/tehillim/admin/__init__.py` e `admin/routes.py`
- `tehillim/tehillim/api/__init__.py` e `api/routes.py`
- `tehillim/tehillim/content/__init__.py`
- `tehillim/tehillim/content/types.py`
- `tehillim/tehillim/content/helpers.py`
- `tehillim/tehillim/content/groups.py`
- `tehillim/tehillim/content/modules/__init__.py`
- `tehillim/tehillim/content/modules/m01_o_que_e_musica.py`
- `tehillim/tehillim/content/demo_games.py` (pode ser vazio por ora)
- `tehillim/tehillim/templates/base_app.html`
- `tehillim/tehillim/templates/modules/home.html` (pode ser mínimo por ora)

### Rodar

No terminal, dentro da pasta `growp` com o ambiente virtual ativado:

```bash
python3 app.py
```

Você deve ver:
```
Abra no navegador: http://127.0.0.1:8000
 * Running on http://127.0.0.1:8000
```

Abra http://127.0.0.1:8000 no navegador. Se aparecer alguma página (mesmo que vazia), o servidor está funcionando.

### Testar login

1. Acesse http://127.0.0.1:8000/login
2. Tente criar uma conta pelo painel do Supabase (Authentication → Users → Invite user) e então logar

---

## 19. Como adicionar conteúdo ao site

Esta seção explica como o sistema de conteúdo funciona e como adicionar módulos regulares, lições do Bona e lições do Pozzoli — sem precisar mexer em rotas, banco de dados ou qualquer outra parte do código.

---

### Como o site descobre o conteúdo automaticamente

O arquivo `tehillim/tehillim/content/modules/__init__.py` varre automaticamente todos os arquivos `.py` da pasta `modules/` toda vez que o servidor inicia. O mecanismo funciona assim:

1. Lista todos os arquivos `.py` da pasta (exceto os que começam com `_`)
2. Para cada arquivo, importa e procura:
   - Uma variável chamada `MODULE` (um único módulo)
   - Uma variável chamada `MODULES` (uma lista ou tupla de módulos)
3. Junta tudo em uma tupla única e ordena pelo número do módulo
4. Esse resultado vira `MODULES`, que é usado em toda a aplicação

**Consequência prática:** para adicionar um módulo ao site, basta criar um arquivo `.py` na pasta certa com a variável `MODULE` ou `MODULES`. O servidor vai encontrá-lo automaticamente na próxima vez que iniciar — ou no próximo deploy.

Não é necessário:
- Registrar o módulo em nenhum lugar
- Criar entradas no banco de dados
- Modificar rotas ou configurações
- Reiniciar o servidor manualmente em produção (o deploy já faz isso)

---

### Números reservados por tipo de conteúdo

Cada módulo tem um número único que determina em qual grupo ele aparece:

| Faixa | Tipo | Grupo no site |
|-------|------|---------------|
| 1 – 10 | Teoria musical básica | Musicalização Infantil |
| 11 – 17 | Leitura musical | Alfabetização Musical |
| 18 – 25 | Prática | Prática e Aplicação |
| 26 – 39 | Harmonia | Teoria e Harmonia |
| 40 – 45 | Avançado | Teoria e Harmonia |
| 101 – 140 | Método Bona (ritmo) | Método Bona |
| 201 – 212 | Método Pozzoli (solfejo) | Método Pozzoli |

O agrupamento é definido em `tehillim/tehillim/content/groups.py` pela função `_by_range(lo, hi)` que seleciona todos os módulos com número entre `lo` e `hi`.

---

### 19.1 — Adicionar um módulo regular (teoria musical)

Crie um arquivo em `tehillim/tehillim/content/modules/` com o padrão de nome `mNN_nome_do_modulo.py`, onde `NN` é o número com dois dígitos.

Exemplo completo — `m02_som_e_silencio.py`:

```python
from tehillim.content.helpers import fill, match, mc, module, tf

MODULE = module(
    2, "som-e-silencio", "Som e Silêncio",
    "Entenda a diferença entre som e silêncio e como ambos formam a música.",
    ("Vibração", "Silêncio musical", "Contraste"),
    theory=(
        "Som é produzido quando um objeto vibra e essa vibração se propaga pelo ar "
        "até nossos ouvidos. O silêncio é a ausência de som — mas em música, o silêncio "
        "não é vazio: ele é uma pausa intencional que dá significado ao que veio antes "
        "e ao que virá depois. Um músico controla tanto os sons quanto os silêncios."
    ),
    visual=(
        "Uma linha do tempo horizontal. Na primeira metade, ondas sonoras coloridas "
        "representam sons de diferentes intensidades. Na segunda metade, a linha fica "
        "plana e cinza — representando o silêncio. A transição entre eles é suave."
    ),
    exercises=(
        mc(
            "O que é necessário para produzir um som?",
            ("Ar parado", "Vibração de um objeto", "Luz intensa", "Temperatura alta"),
            "Vibração de um objeto",
        ),
        tf("O silêncio não tem função na música — só os sons importam.", "Falso"),
        fill(
            "Em música, o ___ é uma pausa intencional entre os sons.",
            ("silêncio", "acorde", "compasso"),
            "silêncio",
        ),
    ),
    game=(
        "EXPERIMENTO: Bata em uma mesa com força e depois toque suavemente. "
        "Sinta a diferença na vibração com a mão espalmada na superfície. "
        "Agora fique em silêncio total por 10 segundos e depois cante uma nota. "
        "O silêncio antes tornou a nota mais especial?"
    ),
    game_kind="game-challenge",
    video_url="https://www.youtube.com/watch?v=SEU_VIDEO_ID",
)
```

**Parâmetros da função `module()`:**

| Parâmetro | Tipo | O que colocar |
|-----------|------|---------------|
| `number` | int | Número único do módulo (ex: `2`) |
| `slug` | str | URL do módulo, só letras minúsculas e hífens (ex: `"som-e-silencio"`) |
| `title` | str | Título que aparece no site (ex: `"Som e Silêncio"`) |
| `description` | str | Frase curta que aparece na listagem de módulos |
| `topics` | tupla de str | Palavras-chave que aparecem como tags |
| `theory` | str | Texto explicativo da etapa de teoria (pode ser longo) |
| `visual` | str | Descrição do elemento visual que acompanha a teoria |
| `exercises` | tupla de Exercise | Exercícios de múltipla escolha, V/F, lacuna ou associação |
| `game` | str | Descrição da atividade prática/jogo |
| `game_kind` | str | Tipo de jogo (veja tabela abaixo) |
| `video_url` | str | URL completa do YouTube (opcional — use `""` se não tiver) |

**Tipos de exercício:**

```python
# Múltipla escolha: pergunta, tupla de opções, resposta correta
mc("Qual instrumento produz som por vibração de cordas?",
   ("Flauta", "Violão", "Tambor", "Trombone"),
   "Violão")

# Verdadeiro ou Falso: afirmação, "Verdadeiro" ou "Falso"
tf("O silêncio não tem função musical.", "Falso")

# Completar lacuna: frase com ___ no lugar da resposta, opções, resposta
fill("O ___ é produzido quando um objeto vibra.",
     ("som", "silêncio", "ritmo"),
     "som")

# Associação: cada item da tupla é "esquerda → direita"
match("Associe o instrumento ao seu grupo:",
      ("Violão → Cordas", "Flauta → Sopro",
       "Tambor → Percussão", "Trompete → Metais"))
```

**Tipos de jogo (`game_kind`):**

| Valor | Descrição visual no site |
|-------|--------------------------|
| `"game-listen"` | Missão de escuta ativa — o aluno sai e volta |
| `"game-challenge"` | Série de checkboxes que o aluno marca ao completar |
| `"game-memory"` | Chips que o aluno clica para fixar tópicos |
| `"game-drag"` | Arrastar e soltar elementos |
| `"game-sort"` | Ordenar uma sequência |
| `"game-quiz"` | Quiz em série rápida |
| `"game-match"` | Associar pares clicando |

---

### 19.2 — Como os grupos são definidos

Os grupos que aparecem na página "Grupos" são definidos em `tehillim/tehillim/content/groups.py`. Para adicionar um novo grupo ou ajustar quais módulos aparecem em cada um, edite esse arquivo:

```python
from tehillim.content.modules import MODULES
from tehillim.content.types import ModuleGroup

def _by_range(lo: int, hi: int) -> tuple:
    """Retorna todos os módulos cujo número está entre lo e hi (inclusive)."""
    return tuple(m for m in MODULES if lo <= m.number <= hi)

GROUPS: tuple[ModuleGroup, ...] = (
    ModuleGroup(
        name="Musicalização Infantil",
        slug="musicalizacao-infantil",
        icon="🟢",
        description="Dê os primeiros passos na música...",
        modules=_by_range(1, 10),   # ← módulos 1 a 10 entram neste grupo
    ),
    ModuleGroup(
        name="Alfabetização Musical",
        slug="alfabetizacao-musical",
        icon="🔵",
        description="Aprenda a ler a linguagem da música...",
        modules=_by_range(11, 17),  # ← módulos 11 a 17
    ),
    # ... outros grupos
)
```

**Para adicionar um novo grupo:** copie um bloco `ModuleGroup(...)` e ajuste o nome, slug, ícone, descrição e o intervalo de números. Os módulos aparecem automaticamente no grupo assim que existirem na pasta `modules/`.

**Para mover um módulo de grupo:** basta alterar seu número (campo `number` no arquivo do módulo) para que fique dentro do intervalo do grupo desejado.

---

## 20. Método Bona (partituras com player)

Os módulos Bona (números 101–140) têm comportamento especial: além do conteúdo pedagógico, exibem uma partitura MusicXML com player de áudio integrado que toca nota por nota.

---

### Como o site trata esses módulos automaticamente

Quando o aluno clica em um módulo Bona, o servidor verifica:

```
número entre 101 e 140?
    ↓ sim
existe o arquivo tehillim/tehillim/static/bona/<slug>.musicxml?
    ↓ sim → renderiza bona_module.html (partitura + player)
    ↓ não → renderiza module.html normal (sem partitura)
```

Você não precisa fazer nada no código para ativar a partitura. Basta colocar o arquivo `.musicxml` na pasta com o nome certo — o site detecta automaticamente.

---

### 20.1 — Criar os módulos Bona no Python

Crie `tehillim/tehillim/content/modules/bona_licoes.py`:

```python
from tehillim.content.types import StudyModule, TrailStep

_BONA_META = [
    # (número, slug, título, bloco)
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
    # ... continue até (140, "bona-licao-40", "Bona — Lição 40", "B4 · Lições 31–40")
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
                slug=f"{slug}-teoria",
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
```

> **Atenção:** os módulos começam com número 101 (não 1), porque a faixa 101–140 é reservada para o Bona. O slug segue o padrão `bona-licao-NN` com dois dígitos — isso é o que o servidor usa para encontrar o arquivo `.musicxml`.

---

### 20.2 — Adicionar a partitura MusicXML

1. Exporte a lição do MuseScore (gratuito: musescore.org) ou outro editor de partituras no formato **MusicXML** (`.musicxml` ou `.xml`).

2. Renomeie o arquivo para corresponder exatamente ao slug do módulo:
   - Lição 1 → `bona-licao-01.musicxml`
   - Lição 15 → `bona-licao-15.musicxml`
   - Lição 37 → `bona-licao-37.musicxml`

3. Coloque o arquivo em `tehillim/tehillim/static/bona/`.

4. Faça o deploy normalmente (`git push origin staging`). O player aparece automaticamente.

**Não precisa fazer mais nada.** O servidor verifica a existência do arquivo em tempo de execução.

---

### 20.3 — Adicionar conteúdo pedagógico a uma lição Bona

Se quiser que além da partitura a lição tenha teoria, exercícios e jogo, substitua o `_blank(...)` pela estrutura completa do módulo regular. Por exemplo, para a lição 1:

```python
from tehillim.content.helpers import fill, mc, module, tf

_LICAO_01 = module(
    101, "bona-licao-01", "Bona — Lição 1",
    "Primeira lição rítmica do Método Bona.",
    ("Ritmo", "Semibreve", "Mínima"),
    theory=(
        "Nesta lição você vai aprender os primeiros valores rítmicos: "
        "a semibreve (4 tempos) e a mínima (2 tempos)..."
    ),
    visual="Partitura simples com semibreves e mínimas em compasso 4/4.",
    exercises=(
        mc("Quantos tempos dura uma semibreve?",
           ("1", "2", "3", "4"), "4"),
        tf("A mínima dura o dobro da semibreve.", "Falso"),
    ),
    game="Bata palmas: 4 tempos lentos (semibreve), depois 2 rápidos (mínima).",
    game_kind="game-challenge",
    video_url="",
)
```

Então no final do arquivo, exporte junto com os demais:

```python
MODULES = (_LICAO_01, *tuple(_blank(n, s, t, g) for n, s, t, g in _BONA_META if n != 101))
```

---

## 20.5 — Método Pozzoli (solfejo)

Os módulos Pozzoli (números 201–212) seguem a mesma lógica dos módulos regulares, mas com partituras melódicas para leitura de notas e solfejo.

---

### 20.5.1 — Criar os módulos Pozzoli no Python

Crie `tehillim/tehillim/content/modules/pozzoli_licoes.py`:

```python
from tehillim.content.helpers import fill, mc, module, tf

_POZZOLI_META = [
    # (número, slug, título, descrição curta)
    (201, "pozzoli-licao-01", "Pozzoli — Lição 1",  "Notas Dó, Ré, Mi na linha central"),
    (202, "pozzoli-licao-02", "Pozzoli — Lição 2",  "Notas Fá, Sol, Lá"),
    (203, "pozzoli-licao-03", "Pozzoli — Lição 3",  "Notas Si, Dó agudo"),
    (204, "pozzoli-licao-04", "Pozzoli — Lição 4",  "Mínimas e semibreves"),
    (205, "pozzoli-licao-05", "Pozzoli — Lição 5",  "Colcheias"),
    (206, "pozzoli-licao-06", "Pozzoli — Lição 6",  "Pausas"),
    (207, "pozzoli-licao-07", "Pozzoli — Lição 7",  "Compasso 3/4"),
    (208, "pozzoli-licao-08", "Pozzoli — Lição 8",  "Compasso 2/4"),
    (209, "pozzoli-licao-09", "Pozzoli — Lição 9",  "Ligaduras"),
    (210, "pozzoli-licao-10", "Pozzoli — Lição 10", "Pontos de aumento"),
    (211, "pozzoli-licao-11", "Pozzoli — Lição 11", "Semicolcheias"),
    (212, "pozzoli-licao-12", "Pozzoli — Lição 12", "Revisão geral"),
]


def _pozzoli(number: int, slug: str, title: str, description: str) -> "StudyModule":
    from tehillim.content.types import StudyModule, TrailStep
    return StudyModule(
        number=number,
        slug=slug,
        title=title,
        description=description,
        topics=("Método Pozzoli", "Solfejo", "Leitura melódica"),
        steps=(
            TrailStep(
                slug=f"{slug}-teoria",
                title="Partitura",
                kind="theory",
                summary="Leia e solfeije a melodia desta lição.",
                body="Use o player para ouvir e acompanhar.",
                prompt="Solfeije a lição e marque quando estiver pronto.",
                options=(),
                answer="",
            ),
        ),
        video_url="",
    )


MODULES: tuple = tuple(_pozzoli(n, s, t, d) for n, s, t, d in _POZZOLI_META)
```

---

### 20.5.2 — Adicionar o grupo Pozzoli em `groups.py`

Abra `tehillim/tehillim/content/groups.py` e adicione o grupo ao final da tupla `GROUPS`:

```python
ModuleGroup(
    name="Método Pozzoli",
    slug="metodo-pozzoli",
    icon="🔴",
    description=(
        "Leitura melódica progressiva baseada no clássico Método Pozzoli. "
        "12 lições de solfejo com partituras do mais simples ao mais elaborado."
    ),
    modules=_by_range(201, 212),
),
```

---

### 20.5.3 — Adicionar arquivos MusicXML do Pozzoli

Diferente do Bona, o Pozzoli não tem uma pasta dedicada no servidor ainda. Você pode:

**Opção A (recomendada): usar a mesma pasta `bona/` com nome diferente**

Coloque os arquivos em `tehillim/tehillim/static/bona/` com o nome do slug:
- `pozzoli-licao-01.musicxml`
- `pozzoli-licao-02.musicxml`
- etc.

O servidor já verifica qualquer arquivo nessa pasta com o nome do slug. Como os números (201–212) estão fora da faixa Bona (101–140), você precisará ajustar a condição em `tehillim/tehillim/modules/routes.py`:

```python
# Linha atual — só detecta Bona:
if 101 <= selected_module.number <= 140:

# Atualizar para detectar Bona E Pozzoli:
if (101 <= selected_module.number <= 140) or (201 <= selected_module.number <= 212):
```

**Opção B: criar uma pasta separada `pozzoli/`**

Se preferir organização separada, crie `tehillim/tehillim/static/pozzoli/`, mova os arquivos para lá e ajuste o caminho em `modules/routes.py`:

```python
_POZZOLI_SHEETS = Path(__file__).resolve().parent.parent / "static" / "pozzoli"

@bp.get("/modulos/<module_slug>")
def module_page(module_slug: str):
    ...
    if 101 <= selected_module.number <= 140:
        sheet_path = _BONA_SHEETS / f"{module_slug}.musicxml"
        has_sheet  = sheet_path.exists()
        return render_template("modules/bona_module.html", ...)

    if 201 <= selected_module.number <= 212:
        sheet_path = _POZZOLI_SHEETS / f"{module_slug}.musicxml"
        has_sheet  = sheet_path.exists()
        return render_template("modules/bona_module.html", ...)  # reutiliza o mesmo template
```

---

### Resumo: o que fazer para cada tipo de conteúdo novo

| O que adicionar | Arquivo a criar/editar | Arquivo estático necessário |
|-----------------|------------------------|-----------------------------|
| Módulo regular | `content/modules/mNN_nome.py` com `MODULE = module(...)` | nenhum |
| Novo grupo de módulos | editar `content/groups.py` | nenhum |
| Lição Bona (só partitura) | já existe em `bona_licoes.py` | `static/bona/bona-licao-NN.musicxml` |
| Lição Bona (partitura + teoria) | editar `bona_licoes.py`, substituir `_blank` por `module(...)` | `static/bona/bona-licao-NN.musicxml` |
| Lição Pozzoli | `content/modules/pozzoli_licoes.py` + editar `groups.py` | `static/bona/pozzoli-licao-NN.musicxml` |

**Em todos os casos:** após salvar os arquivos, basta fazer `git push origin staging` para o conteúdo aparecer no staging automaticamente. Nenhum restart manual, nenhuma migração de banco de dados.

---

## 21. Dashboard do professor

O dashboard do professor é acessado em `/dashboard`. Ele exibe:
- Lista de todos os alunos cadastrados com progresso e última atividade
- Controle de acesso: liberar/bloquear módulos para cada aluno
- Gravações de áudio dos alunos com player
- Comentários por aluno/módulo

### Criar um usuário professor

1. Acesse seu Supabase → Authentication → Users
2. Encontre o usuário que será professor
3. No painel SQL Editor do Supabase, rode:
   ```sql
   -- Substitua pelo email real do professor
   update auth.users
   set raw_user_meta_data = raw_user_meta_data || '{"role": "teacher"}'::jsonb
   where email = 'professor@exemplo.com';
   ```

Ou use o painel Admin em `/admin` para definir o papel de professor visualmente.

> O template `dashboard.html` e o script `dashboard.js` devem ser copiados do projeto original.

---

## 22. Painel admin

O painel admin é acessado em `/admin`. Permite:
- Criar novos usuários (e-mail, senha, nome)
- Definir usuário como professor
- Resetar senhas
- Excluir usuários

> O template `admin.html` e o script `admin.js` devem ser copiados do projeto original.

---

## 23. Ordem final de montagem

Siga esta sequência para montar o projeto sem erros:

**Fase 1 — Infraestrutura (sem código de app)**
1. Criar conta Supabase e anotar as 3 chaves
2. Criar bucket `recordings` (privado) no Storage do Supabase
3. Rodar o `setup.sql` no SQL Editor do Supabase
4. Criar estrutura de pastas (seção 3)
5. Criar ambiente virtual e instalar dependências
6. Criar `.env` com as chaves

**Fase 2 — Backend Python**
7. Criar `tehillim/tehillim/config.py`
8. Criar `tehillim/tehillim/extensions.py`
9. Criar `tehillim/tehillim/content/types.py`
10. Criar `tehillim/tehillim/content/helpers.py`
11. Criar `tehillim/tehillim/content/modules/__init__.py`
12. Criar o primeiro módulo: `content/modules/m01_o_que_e_musica.py`
13. Criar `tehillim/tehillim/content/demo_games.py` (pode ser vazio: `DEMO_GAMES = []`)
14. Criar `tehillim/tehillim/content/groups.py`
15. Criar `tehillim/tehillim/content/__init__.py`
16. Criar `tehillim/tehillim/auth/__init__.py` e `auth/routes.py`
17. Criar `tehillim/tehillim/modules/__init__.py` e `modules/routes.py`
18. Criar `tehillim/tehillim/admin/__init__.py` e `admin/routes.py`
19. Criar `tehillim/tehillim/api/__init__.py` e `api/routes.py`
20. Criar `tehillim/tehillim/__init__.py` com `create_app()`
21. Criar `tehillim/app.py`

**Fase 3 — Testar o backend**
22. Rodar `python3 app.py` e verificar que sobe sem erros
23. Abrir http://127.0.0.1:8000/api/modules no navegador — deve retornar JSON

**Fase 4 — Frontend: CSS e JavaScript**
24. Criar `tehillim/tehillim/static/css/styles.css` (copiar do original)
25. Criar `tehillim/tehillim/static/css/games.css` (copiar do original)
26. Criar `tehillim/tehillim/static/css/dashboard.css` (copiar do original)
27. Criar `tehillim/tehillim/static/css/admin.css` (copiar do original)
28. Criar `tehillim/tehillim/static/js/auth.js` (copiar do original)
29. Criar `tehillim/tehillim/static/js/app.js` (copiar do original)
30. Criar `tehillim/tehillim/static/js/audio.js` (copiar do original)
31. Criar `tehillim/tehillim/static/js/vexflow-utils.js` (copiar do original)
32. Criar `tehillim/tehillim/static/js/recorder.js` (copiar do original)
33. Criar `tehillim/tehillim/static/js/games.js` (copiar do original)
34. Criar `tehillim/tehillim/static/js/dashboard.js` (copiar do original)
35. Criar `tehillim/tehillim/static/js/admin.js` (copiar do original)
36. Criar `tehillim/tehillim/static/js/group.js` (copiar do original)

**Fase 5 — Frontend: Templates HTML**
37. Criar `tehillim/tehillim/templates/base.html`
38. Criar `tehillim/tehillim/templates/base_app.html`
39. Criar `tehillim/tehillim/templates/auth/login.html` (copiar do original)
40. Criar `tehillim/tehillim/templates/modules/home.html` (copiar do original)
41. Criar `tehillim/tehillim/templates/modules/grupos.html` (copiar do original)
42. Criar `tehillim/tehillim/templates/modules/group.html` (copiar do original)
43. Criar `tehillim/tehillim/templates/modules/trilhas.html` (copiar do original)
44. Criar `tehillim/tehillim/templates/modules/module.html` (copiar do original)
45. Criar `tehillim/tehillim/templates/modules/bona_module.html` (copiar do original)
46. Criar `tehillim/tehillim/templates/modules/bona_player.html` (copiar do original)
47. Criar `tehillim/tehillim/templates/pages/aulas.html` (copiar do original)
48. Criar `tehillim/tehillim/templates/pages/desempenho.html` (copiar do original)
49. Criar `tehillim/tehillim/templates/pages/conquistas.html` (copiar do original)
50. Criar `tehillim/tehillim/templates/pages/configuracoes.html` (copiar do original)
51. Criar `tehillim/tehillim/templates/admin/dashboard.html` (copiar do original)
52. Criar `tehillim/tehillim/templates/admin/admin.html` (copiar do original)

**Fase 6 — Conteúdo**
53. Criar os demais módulos (`m02` a `m45`) em `tehillim/tehillim/content/modules/`
54. Criar `bona_licoes.py` em `tehillim/tehillim/content/modules/`
55. Adicionar arquivos `.musicxml` em `tehillim/tehillim/static/bona/`

**Fase 7 — Teste final**
56. Rodar o servidor e testar o login
57. Criar um usuário de teste pelo Supabase ou pelo painel admin
58. Navegar por todas as páginas
59. Testar um módulo de estudo completo (todas as etapas)
60. Testar o dashboard do professor

---

## Dicas de depuração

**Servidor não sobe:**
- Verifique se o ambiente virtual está ativo: deve aparecer `(.venv)` no terminal
- Verifique se o `.env` existe e tem as 3 variáveis
- Rode `python3 -c "from tehillim import create_app; create_app(); print('OK')"` para ver o erro

**Login não funciona:**
- Verifique se as chaves Supabase no `.env` são as corretas (URL, anon key)
- No Supabase → Authentication → Settings → verifique se "Email" está habilitado
- Abra o console do navegador (F12 → Console) e procure erros em vermelho

**Progresso não salva:**
- Verifique se as tabelas foram criadas no Supabase
- Abra o console do navegador e procure erros de rede (F12 → Network)
- Confirme que o RLS está habilitado nas tabelas

**Módulo não aparece:**
- Verifique se o arquivo do módulo está em `content/modules/`
- Confirme que o nome do arquivo **não começa com underscore** (`_`)
- Confirme que o arquivo exporta `MODULE` ou `MODULES` (maiúsculas)
- Acesse http://127.0.0.1:8000/api/modules para ver se o módulo aparece no JSON

**Partitura Bona não aparece:**
- Verifique se o arquivo `.musicxml` está em `static/bona/`
- O nome do arquivo deve ser exatamente igual ao slug do módulo: `bona-licao-01.musicxml`

---

## 24. Deploy na internet (Google Cloud Run)

Esta seção explica como colocar a plataforma no ar usando o **Google Cloud Run**, que é gratuito para o volume de acesso de ~15 alunos e escala automaticamente conforme cresce.

### Por que Cloud Run?

- **Gratuito na prática:** o free tier inclui 2 milhões de requisições por mês e 360.000 GB-segundos de memória. Para 15 alunos, o custo será R$ 0,00.
- **Escala para zero:** quando ninguém está usando, o container para — você não paga por servidor ocioso.
- **Sem manutenção:** você não precisa configurar servidores, sistemas operacionais ou atualizações de segurança.
- **SSL incluído:** o Google gera o certificado HTTPS automaticamente.

---

### Passo 24.1 — Criar conta e projeto no Google Cloud

1. Acesse https://console.cloud.google.com
2. Faça login com uma conta Google.
3. Clique em **"Select a project"** → **"New Project"**.
4. Dê o nome `tehillim` e clique em **Create**.
5. Aguarde o projeto ser criado e selecione-o.

> **Atenção:** o Google exige um cartão de crédito para criar uma conta, mas não cobra nada enquanto você estiver dentro do free tier. Você receberá alertas antes de qualquer cobrança.

---

### Passo 24.2 — Instalar o Google Cloud CLI (`gcloud`)

O `gcloud` é uma ferramenta de linha de comando para controlar serviços do Google Cloud.

**No Mac:**
```
brew install google-cloud-sdk
```

Se não tiver o Homebrew instalado:
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**No Linux/WSL:**
```
curl -O https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz
tar -xf google-cloud-cli-linux-x86_64.tar.gz
./google-cloud-sdk/install.sh
```

Após a instalação, feche e reabra o terminal. Depois faça login:
```
gcloud auth login
```

Uma janela do navegador vai abrir pedindo para você entrar com sua conta Google. Autorize.

Em seguida, defina o projeto ativo:
```
gcloud config set project tehillim
```

> Se o nome `tehillim` não funcionar (projetos precisam de IDs únicos globais), use o ID exato que apareceu na hora de criar — algo como `tehillim-123456`.

---

### Passo 24.3 — Habilitar as APIs necessárias

Rode os dois comandos abaixo:
```
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

Aguarde alguns segundos até os dois comandos completarem.

---

### Passo 24.4 — Criar o arquivo `Dockerfile`

O Dockerfile instrui o Google Cloud como empacotar e rodar sua aplicação.

Na raiz do projeto (mesma pasta onde está `app.py`), crie o arquivo `Dockerfile` com este conteúdo exato:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "app.py"]
```

**O que cada linha faz:**
- `FROM python:3.11-slim` — usa uma imagem Python 3.11 mínima como base
- `WORKDIR /app` — define `/app` como pasta de trabalho dentro do container
- `COPY requirements.txt .` — copia o arquivo de dependências
- `RUN pip install ...` — instala todas as dependências Python
- `COPY . .` — copia todos os arquivos do projeto
- `ENV PORT=8080` — define a variável de ambiente que o Cloud Run espera
- `CMD ["python", "app.py"]` — comando para iniciar a aplicação

---

### Passo 24.5 — Criar o arquivo `.dockerignore`

Este arquivo evita que arquivos desnecessários sejam enviados ao Google Cloud, tornando o deploy mais rápido.

Crie o arquivo `.dockerignore` na raiz do projeto:

```
.env
.venv
venv
__pycache__
*.pyc
*.pyo
.git
.gitignore
*.md
.DS_Store
```

---

### Passo 24.6 — Ajustar o `app.py` para usar a porta correta

O Cloud Run passa a porta que a aplicação deve escutar via variável de ambiente `$PORT`. Seu `app.py` precisa ler essa variável.

Abra `app.py` e certifique-se de que a última linha está assim:

```python
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
```

**Mudanças importantes:**
- `host="0.0.0.0"` — permite conexões de fora do container (obrigatório no Cloud Run)
- `port=int(os.environ.get("PORT", 8000))` — usa a porta do ambiente, com fallback para 8000 local
- `debug=False` — nunca use `debug=True` em produção (expõe informações sensíveis)

---

### Passo 24.7 — Fazer o deploy

Com tudo preparado, rode o comando de deploy diretamente do terminal, dentro da pasta raiz do projeto:

```
gcloud run deploy tehillim \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "SUPABASE_URL=https://XXXXXXXX.supabase.co,SUPABASE_ANON_KEY=eyJhb...,SUPABASE_SERVICE_ROLE_KEY=eyJhb..."
```

**Substitua os valores:**
- `SUPABASE_URL` — a URL do seu projeto Supabase (Project Settings → API → Project URL)
- `SUPABASE_ANON_KEY` — a chave pública anon (Project Settings → API → anon public)
- `SUPABASE_SERVICE_ROLE_KEY` — a chave privada service_role (Project Settings → API → service_role)

**O que acontece durante o deploy:**
1. O `gcloud` empacota seus arquivos em um container Docker
2. Envia para o Google Artifact Registry
3. Cria o serviço no Cloud Run
4. Exibe a URL pública ao final, algo como:
   ```
   Service URL: https://tehillim-abc123-uc.a.run.app
   ```

O processo leva entre 2 e 5 minutos na primeira vez.

---

### Passo 24.8 — Testar o deploy

Abra a URL que apareceu no terminal (formato `https://tehillim-xxxxx-uc.a.run.app`) no navegador. Você deve ver sua plataforma funcionando normalmente.

Se aparecer algum erro, veja os logs:
```
gcloud run services logs read tehillim --region us-central1
```

---

### Passo 24.9 — Atualizar o deploy no futuro

Toda vez que você fizer alterações no código e quiser publicar, rode o mesmo comando do passo 24.7. O Cloud Run vai substituir a versão anterior com zero downtime.

---

## 25. Domínio próprio (tehillim.com.br)

Esta seção explica como apontar o domínio `tehillim.com.br` para o seu servidor no Cloud Run.

A arquitetura ficará assim:

```
Aluno acessa tehillim.com.br
        ↓
  Cloudflare (DNS + CDN gratuito)
        ↓
  Google Cloud Run (seu app Flask)
        ↓
  Supabase (banco de dados + auth)
```

---

### Passo 25.1 — Registrar o domínio tehillim.com.br

1. Acesse https://registro.br — é o único registrador oficial de domínios `.com.br` no Brasil.
2. Crie uma conta (ou faça login se já tiver).
3. Na busca, pesquise `tehillim.com.br` e clique em **Registrar**.
4. Preencha os dados do titular e finalize o pagamento (em torno de R$ 40/ano).
5. Aguarde a confirmação por e-mail. O domínio é ativado em alguns minutos.

---

### Passo 25.2 — Criar conta no Cloudflare

O Cloudflare vai gerenciar os DNS do seu domínio de graça, e ainda oferece CDN e proteção DDoS.

1. Acesse https://cloudflare.com e crie uma conta gratuita.
2. Clique em **"Add a Site"**.
3. Digite `tehillim.com.br` e clique em **Continue**.
4. Selecione o plano **Free** e clique em **Continue**.
5. O Cloudflare vai tentar ler os registros DNS atuais do domínio. Clique em **Continue** novamente.
6. Ao final, o Cloudflare mostrará dois **nameservers** — eles terão um formato assim:
   ```
   alice.ns.cloudflare.com
   bob.ns.cloudflare.com
   ```
   Anote esses dois endereços — você vai precisar deles no próximo passo.

---

### Passo 25.3 — Apontar o domínio para o Cloudflare no registro.br

1. Volte para https://registro.br e acesse **Meus Domínios**.
2. Clique em `tehillim.com.br`.
3. Procure a seção **"Servidores DNS"** ou **"Nameservers"**.
4. Substitua os nameservers existentes pelos dois que o Cloudflare forneceu.
5. Salve. A propagação pode levar até 24 horas, mas geralmente leva menos de 1 hora.

---

### Passo 25.4 — Mapear o domínio no Cloud Run

O Cloud Run precisa ser informado de que `tehillim.com.br` pertence a você.

1. Acesse https://console.cloud.google.com → **Cloud Run** → clique no serviço `tehillim`.
2. Clique na aba **"Custom Domains"** (Domínios personalizados).
3. Clique em **"Add Custom Domain"**.
4. Digite `tehillim.com.br` e clique em **Continue**.
5. O Google vai exibir registros DNS para você adicionar. Eles serão do tipo **A** e **AAAA** (ou CNAME para subdomínios), com valores como:
   ```
   Tipo: A    Nome: @    Valor: 216.239.32.21
   Tipo: A    Nome: @    Valor: 216.239.34.21
   Tipo: A    Nome: @    Valor: 216.239.36.21
   Tipo: A    Nome: @    Valor: 216.239.38.21
   Tipo: AAAA Nome: @    Valor: 2001:4860:4802:32::15
   ... (e outros)
   ```
   Anote todos esses registros.

> **Atenção:** os valores reais dos IPs serão exibidos no console — use sempre os valores que o Google mostrar, não os do exemplo acima.

---

### Passo 25.5 — Adicionar os registros DNS no Cloudflare

1. No painel do Cloudflare, acesse seu site `tehillim.com.br` → **DNS** → **Records**.
2. Para cada registro que o Google forneceu no passo anterior, clique em **"Add record"** e preencha:
   - **Type:** A (ou AAAA)
   - **Name:** @ (representa o domínio raiz `tehillim.com.br`)
   - **IPv4 address:** o valor fornecido pelo Google
   - **Proxy status:** clique no ícone de nuvem para deixar **laranja** (Proxied) — isso ativa o CDN e a proteção do Cloudflare
3. Repita para todos os registros.

Se o Cloud Run também forneceu um registro para `www.tehillim.com.br`, adicione também com **Name:** `www`.

---

### Passo 25.6 — Verificar a propriedade do domínio

Após adicionar os registros DNS, volte ao console do Cloud Run e clique em **"Verify"**. O Google vai checar se os registros estão propagados.

A verificação pode levar de alguns minutos até 1 hora. O status vai mudar de "Pending" para "Active".

---

### Passo 25.7 — Certificado SSL (HTTPS)

Não é necessário fazer nada. O Google emite o certificado SSL automaticamente assim que o domínio é verificado. Após a verificação, seu site já estará acessível em:

```
https://tehillim.com.br
```

com o cadeado verde de segurança no navegador.

---

### Passo 25.8 — Redirecionar www para o domínio principal (opcional)

Se quiser que `www.tehillim.com.br` também funcione e redirecione para `tehillim.com.br`:

1. No Cloud Run → Custom Domains → Add Custom Domain → digite `www.tehillim.com.br`.
2. Adicione o registro CNAME fornecido no DNS do Cloudflare.
3. Aguarde a verificação.

Alternativamente, no próprio Cloudflare você pode criar uma **Page Rule** de redirecionamento de `www.tehillim.com.br/*` para `https://tehillim.com.br/$1`.

---

### Passo 25.9 — Atualizar o Supabase com o novo domínio

Após o domínio estar ativo, você precisa informar ao Supabase que `tehillim.com.br` é uma origem válida para login.

1. Acesse seu projeto no Supabase → **Authentication** → **URL Configuration**.
2. Em **"Site URL"**, substitua qualquer valor existente por:
   ```
   https://tehillim.com.br
   ```
3. Em **"Redirect URLs"**, adicione:
   ```
   https://tehillim.com.br/**
   ```
4. Clique em **Save**.

Isso é necessário para que os magic links e redirecionamentos de login funcionem corretamente com o domínio próprio.

---

### Resumo do fluxo completo de deploy e domínio

```
1. gcloud run deploy tehillim --source .    ← publica o app
2. registro.br → compra tehillim.com.br     ← registra o domínio
3. cloudflare.com → adiciona o site         ← coloca Cloudflare como DNS
4. registro.br → troca nameservers          ← aponta para Cloudflare
5. Cloud Run → Custom Domains               ← mapeia o domínio
6. Cloudflare → DNS Records                 ← adiciona registros do Google
7. Supabase → URL Configuration             ← atualiza origem do login
```

---

### Dicas de depuração (deploy e domínio)

**O deploy falhou:**
- Leia a mensagem de erro com atenção. Erros comuns:
  - `ModuleNotFoundError` — alguma dependência não está no `requirements.txt`. Adicione e tente novamente.
  - `Port 8080 is not listening` — o `app.py` não está usando `host="0.0.0.0"`. Corrija e tente novamente.
- Para ver os logs completos:
  ```
  gcloud run services logs read tehillim --region us-central1 --limit 50
  ```

**O site abre mas dá erro 500:**
- É um erro na aplicação, não no Cloud Run. Veja os logs acima para identificar qual linha causou o erro.

**O domínio não abre (ERR_NAME_NOT_RESOLVED):**
- A propagação DNS ainda não chegou. Aguarde até 1 hora.
- Verifique se os nameservers no registro.br estão corretos: acesse https://dnschecker.org, busque `tehillim.com.br` e veja se os nameservers são os do Cloudflare.

**O site abre com aviso "não seguro" (sem HTTPS):**
- O certificado SSL ainda está sendo emitido pelo Google. Aguarde até 30 minutos após a verificação do domínio no Cloud Run.

**Login com magic link não funciona após trocar de domínio:**
- Verifique se o Supabase está com a URL correta (passo 25.9). O link de e-mail vai redirecionar para a URL antiga se não for atualizado.

---

---

## 26. Versionamento e deploy automático (GitHub + CI/CD)

Esta seção explica como versionar o código no GitHub e configurar deploy automático: toda mudança enviada para o branch `staging` vai para o ambiente de testes, e toda mudança aprovada e enviada para `main` vai para produção.

### Como o fluxo vai funcionar

```
Você edita o código no computador
          ↓
   git push → branch staging
          ↓  (automático)
   GitHub Actions detecta o push
          ↓  (automático)
   Deploy em tehillim-staging.run.app   ← você testa aqui
          ↓  (você aprova, abre um Pull Request)
   PR: staging → main  →  você clica em Merge
          ↓  (automático)
   GitHub Actions detecta o merge
          ↓  (automático)
   Deploy em tehillim.com.br            ← produção
```

Você nunca precisa rodar comandos de deploy manualmente. Tudo acontece ao fazer `git push`.

---

### Passo 26.1 — Criar conta no GitHub

Se ainda não tiver uma conta:

1. Acesse https://github.com e clique em **Sign up**.
2. Escolha um nome de usuário, e-mail e senha.
3. Confirme o e-mail que o GitHub vai enviar.

---

### Passo 26.2 — Criar o repositório no GitHub

1. Após fazer login no GitHub, clique no botão **"+"** no canto superior direito → **"New repository"**.
2. Preencha:
   - **Repository name:** `tehillim`
   - **Description:** `Plataforma de aprendizado musical`
   - **Visibility:** selecione **Private** (para não expor seu código publicamente)
3. **Não marque** nenhuma das opções de inicialização (README, .gitignore, license) — faremos isso manualmente.
4. Clique em **"Create repository"**.

O GitHub vai exibir uma página com instruções. Copie o endereço do repositório — terá o formato:
```
https://github.com/seu-usuario/tehillim.git
```

---

### Passo 26.3 — Criar o arquivo `.gitignore`

O `.gitignore` lista arquivos que **não** devem ser enviados ao GitHub — principalmente o `.env` que contém suas senhas.

Na raiz do projeto, crie o arquivo `.gitignore`:

```
# Variáveis de ambiente (NUNCA enviar para o GitHub)
.env

# Ambiente virtual Python
.venv/
venv/
env/

# Cache Python
__pycache__/
*.pyc
*.pyo
*.pyd

# Arquivos do sistema operacional
.DS_Store
Thumbs.db

# Arquivos temporários
*.log
*.tmp
```

---

### Passo 26.4 — Inicializar o Git localmente e enviar para o GitHub

Abra o terminal na pasta raiz do projeto e rode os comandos abaixo **em ordem**:

**Inicializa o Git:**
```
git init
```

**Adiciona todos os arquivos (exceto os do .gitignore):**
```
git add .
```

**Cria o primeiro commit:**
```
git commit -m "primeiro commit: projeto tehillim"
```

**Renomeia o branch principal para `main`:**
```
git branch -M main
```

**Conecta ao repositório remoto no GitHub** (substitua pelo endereço do seu repositório):
```
git remote add origin https://github.com/seu-usuario/tehillim.git
```

**Envia o código para o GitHub:**
```
git push -u origin main
```

O terminal vai pedir seu usuário e senha do GitHub. Para a senha, **não use sua senha normal** — o GitHub exige um "Personal Access Token". Veja como criar no próximo passo.

---

### Passo 26.5 — Criar um Personal Access Token no GitHub

O GitHub não aceita senha comum para operações via terminal. Você precisa criar um token de acesso.

1. No GitHub, clique na sua foto (canto superior direito) → **Settings**.
2. No menu lateral esquerdo, role até o final e clique em **"Developer settings"**.
3. Clique em **"Personal access tokens"** → **"Tokens (classic)"**.
4. Clique em **"Generate new token"** → **"Generate new token (classic)"**.
5. Preencha:
   - **Note:** `tehillim-deploy` (um nome qualquer para lembrar o uso)
   - **Expiration:** selecione **"No expiration"** (ou 1 year, conforme preferir)
   - **Scopes:** marque apenas **`repo`** (acesso completo a repositórios)
6. Role até o final e clique em **"Generate token"**.
7. **Copie o token imediatamente** — ele só aparece uma vez. Salve em um local seguro (como um gerenciador de senhas).

Na próxima vez que o terminal pedir senha, cole este token no lugar da senha.

---

### Passo 26.6 — Criar o branch `staging`

O branch `staging` é onde você vai enviar mudanças para testar antes de ir para produção.

```
git checkout -b staging
git push -u origin staging
```

A partir de agora você tem dois branches no GitHub:
- `main` → produção (tehillim.com.br)
- `staging` → testes (tehillim-staging.run.app)

---

### Passo 26.7 — Criar os arquivos de workflow do GitHub Actions

O GitHub Actions é um sistema que executa tarefas automaticamente quando você faz push. As tarefas são definidas em arquivos `.yml` dentro da pasta `.github/workflows/`.

Crie a pasta:
```
mkdir -p .github/workflows
```

**Arquivo 1 — Deploy automático para staging**

Crie o arquivo `.github/workflows/deploy-staging.yml`:

```yaml
name: Deploy → Staging

on:
  push:
    branches: [staging]

jobs:
  deploy:
    name: Deploy to Cloud Run (staging)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout código
        uses: actions/checkout@v4

      - name: Autenticar no Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy no Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: tehillim-staging
          region: us-central1
          source: .
          flags: --allow-unauthenticated
          env_vars: |
            SUPABASE_URL=${{ secrets.SUPABASE_URL }}
            SUPABASE_ANON_KEY=${{ secrets.SUPABASE_ANON_KEY }}
            SUPABASE_SERVICE_ROLE_KEY=${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

**Arquivo 2 — Deploy automático para produção**

Crie o arquivo `.github/workflows/deploy-prod.yml`:

```yaml
name: Deploy → Produção

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy to Cloud Run (produção)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout código
        uses: actions/checkout@v4

      - name: Autenticar no Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Deploy no Cloud Run
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: tehillim
          region: us-central1
          source: .
          flags: --allow-unauthenticated
          env_vars: |
            SUPABASE_URL=${{ secrets.SUPABASE_URL }}
            SUPABASE_ANON_KEY=${{ secrets.SUPABASE_ANON_KEY }}
            SUPABASE_SERVICE_ROLE_KEY=${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
```

**O que cada parte faz:**
- `on: push: branches: [staging]` — define quando o workflow roda (ao fazer push no branch staging)
- `actions/checkout@v4` — baixa o código do repositório dentro da máquina do GitHub
- `google-github-actions/auth@v2` — usa sua chave GCP para autenticar
- `google-github-actions/deploy-cloudrun@v2` — faz o deploy no Cloud Run
- `${{ secrets.GCP_SA_KEY }}` — lê a chave secreta que você vai configurar no próximo passo

---

### Passo 26.8 — Criar a Service Account no Google Cloud

A Service Account é uma "conta de serviço" que o GitHub vai usar para se autenticar no Google Cloud e fazer deploys em seu nome.

1. Acesse https://console.cloud.google.com → selecione seu projeto `tehillim`.
2. No menu lateral, procure **"IAM & Admin"** → **"Service Accounts"**.
3. Clique em **"Create Service Account"**.
4. Preencha:
   - **Service account name:** `github-deploy`
   - **Service account ID:** vai preencher automaticamente como `github-deploy`
   - **Description:** `Conta usada pelo GitHub Actions para fazer deploy`
5. Clique em **"Create and Continue"**.
6. Na etapa **"Grant this service account access to project"**, adicione as seguintes 4 permissões clicando em **"Add another role"** para cada uma:
   - `Cloud Run Admin`
   - `Storage Admin`
   - `Service Account User`
   - `Cloud Build Editor`
7. Clique em **"Continue"** e depois em **"Done"**.

---

### Passo 26.9 — Baixar a chave JSON da Service Account

1. Na lista de Service Accounts, clique na que você acabou de criar (`github-deploy@tehillim-...`).
2. Clique na aba **"Keys"**.
3. Clique em **"Add Key"** → **"Create new key"**.
4. Selecione o formato **JSON** e clique em **"Create"**.
5. Um arquivo `.json` vai ser baixado automaticamente no seu computador. **Guarde esse arquivo com segurança** — ele dá acesso total ao seu projeto GCP.

---

### Passo 26.10 — Habilitar o Cloud Build

O Cloud Run usa o Cloud Build para compilar os containers. Você precisa habilitá-lo:

```
gcloud services enable cloudbuild.googleapis.com
```

---

### Passo 26.11 — Adicionar os Secrets no GitHub

Os Secrets são variáveis seguras armazenadas no GitHub. O código dos workflows lê esses valores sem expô-los.

1. No GitHub, acesse seu repositório `tehillim`.
2. Clique em **"Settings"** (aba no topo do repositório).
3. No menu lateral esquerdo, clique em **"Secrets and variables"** → **"Actions"**.
4. Para cada item abaixo, clique em **"New repository secret"**, preencha o **Name** e o **Secret**, e clique em **"Add secret"**:

---

**Secret 1: GCP_SA_KEY**

- **Name:** `GCP_SA_KEY`
- **Secret:** abra o arquivo `.json` que você baixou no passo anterior em um editor de texto, selecione **todo o conteúdo** (Ctrl+A) e cole aqui.

---

**Secret 2: SUPABASE_URL**

- **Name:** `SUPABASE_URL`
- **Secret:** a URL do seu projeto Supabase. Encontre em: Supabase → Project Settings → API → Project URL.
  Formato: `https://xxxxxxxxxxxxxxxx.supabase.co`

---

**Secret 3: SUPABASE_ANON_KEY**

- **Name:** `SUPABASE_ANON_KEY`
- **Secret:** a chave pública anon. Encontre em: Supabase → Project Settings → API → `anon` `public`.

---

**Secret 4: SUPABASE_SERVICE_ROLE_KEY**

- **Name:** `SUPABASE_SERVICE_ROLE_KEY`
- **Secret:** a chave privada service_role. Encontre em: Supabase → Project Settings → API → `service_role` `secret`.

> **Atenção:** a `service_role` key tem acesso total ao banco de dados. Nunca compartilhe ela publicamente.

Ao final você deve ter 4 secrets cadastrados:
```
GCP_SA_KEY
SUPABASE_URL
SUPABASE_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY
```

---

### Passo 26.12 — Fazer o primeiro push e verificar o deploy

Agora é a hora de testar se tudo funciona. Vamos fazer um push para o branch `staging`:

**Certifique-se de estar no branch staging:**
```
git checkout staging
```

**Adicione os novos arquivos criados (workflows e .gitignore):**
```
git add .github/ .gitignore Dockerfile .dockerignore
git commit -m "adiciona workflows de deploy e arquivos de configuração"
git push origin staging
```

Agora acesse o GitHub, clique na aba **"Actions"** do seu repositório. Você verá o workflow `Deploy → Staging` em execução. Clique nele para ver o progresso em tempo real.

Se tudo estiver correto, ao final você verá:
```
✓ Deploy → Staging  (em verde)
```

O Cloud Run vai gerar uma URL de staging automaticamente, no formato:
```
https://tehillim-staging-xxxxxxx-uc.a.run.app
```

Você pode ver essa URL em: Google Cloud Console → Cloud Run → serviço `tehillim-staging` → URL.

---

### Passo 26.13 — Promover para produção (o fluxo do dia a dia)

Quando você testar no staging e quiser publicar em produção:

1. No GitHub, acesse seu repositório.
2. Clique em **"Pull requests"** → **"New pull request"**.
3. Configure:
   - **base:** `main`
   - **compare:** `staging`
4. Clique em **"Create pull request"**.
5. Adicione um título descrevendo o que está sendo publicado (ex: `Adiciona novo módulo de teoria musical`).
6. Clique em **"Create pull request"** novamente.
7. Revise as mudanças mostradas.
8. Clique em **"Merge pull request"** → **"Confirm merge"**.

O GitHub Actions vai detectar o merge no `main` e disparar automaticamente o workflow `Deploy → Produção`. Em 2-5 minutos, as mudanças estarão em `tehillim.com.br`.

---

### Passo 26.14 — Fluxo de trabalho do dia a dia

Após a configuração inicial, seu fluxo para qualquer mudança será:

**1. Certifique-se de estar no branch staging:**
```
git checkout staging
```

**2. Faça suas alterações nos arquivos.**

**3. Salve e envie para o GitHub:**
```
git add .
git commit -m "descreva o que você mudou"
git push origin staging
```

**4. Aguarde o deploy automático** (2-5 minutos) e teste em `tehillim-staging.run.app`.

**5. Se aprovado, vá ao GitHub, abra um Pull Request de `staging` → `main` e faça o merge.**

**6. Produção é atualizada automaticamente.**

---

### Dicas de depuração (GitHub Actions)

**O workflow não aparece na aba Actions:**
- Verifique se os arquivos `.yml` estão exatamente em `.github/workflows/` — a pasta `.github` deve estar na raiz do projeto (mesma pasta do `app.py`).
- Verifique se o arquivo foi enviado para o GitHub com `git push`.

**O workflow falhou com erro de autenticação:**
- Verifique se o secret `GCP_SA_KEY` contém o conteúdo completo do arquivo JSON (incluindo as chaves `{` e `}`).
- Verifique se a Service Account tem as 4 permissões do passo 26.8.

**O workflow falhou com erro de permissão no Cloud Build:**
- No Google Cloud Console, acesse IAM → encontre a Service Account → verifique se `Cloud Build Editor` está na lista de permissões.
- Rode: `gcloud services enable cloudbuild.googleapis.com`

**O workflow passou mas o site não abre:**
- Acesse Google Cloud → Cloud Run → serviço `tehillim-staging` → Logs.
- Procure erros em vermelho. Geralmente é uma variável de ambiente faltando ou erro no código Python.

**Quero desfazer uma mudança que fui para produção:**
- No GitHub, acesse o Pull Request que foi mergeado → clique em **"Revert"**.
- Isso cria um novo PR que desfaz as mudanças. Confirme o merge e o deploy automático vai reverter a produção.

---

*Blueprint gerado em 25 de abril de 2026.*
