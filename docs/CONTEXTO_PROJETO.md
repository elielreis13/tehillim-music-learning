# Tehillim — Briefing Completo do Projeto

Use este documento para iniciar conversas sobre o projeto em qualquer chat de IA.
Comece com: *"Estou desenvolvendo uma plataforma de educação musical. Aqui está o contexto completo:"*

---

## O que é

**Tehillim** é uma plataforma web de educação musical voltada para alunos de música cristã/eclesiástica no Brasil. O professor (Eliel Reis) libera módulos individualmente para cada aluno, que progride em trilhas de estudo com gamificação (XP, streaks, conquistas).

URL de produção: implantado no Google Cloud Run via GitHub Actions.

---

## Stack técnica

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.10 + Flask 3.x com Blueprints |
| Frontend | Jinja2 templates + Tailwind CSS (CDN) + inline styles |
| Banco de dados | Supabase (PostgreSQL) com RLS |
| Auth | Supabase Auth + sessão Flask (JWT no servidor) |
| Storage | Supabase Storage (bucket `recordings` para áudios, bucket `books` para PDFs) |
| Sheet music | OpenSheetMusicDisplay (OSMD) 1.8.7 + Tone.js 14 (player de partituras MusicXML) |
| Deploy | Docker → Google Cloud Run (staging + prod) via GitHub Actions |
| Analytics | Google Tag Manager (GTM-MCSBVW3L) |

---

## Estrutura de pastas

```
tehillim/
  admin/          → blueprint admin (professor)
  api/            → blueprint API REST interna
  auth/           → blueprint auth (login/logout/registro)
  modules/        → blueprint de páginas (grupos, módulos, trilhas)
  public/         → blueprint público (landing page)
  content/
    modules/      → arquivos .md de cada módulo (fonte de conteúdo)
      split/      → 106 módulos ativos em .md
      bona_licoes.py → define as 40 lições do Método Bona
    md_loader.py  → parser dos .md para objetos StudyModule
  static/
    bona/         → arquivos MusicXML das lições (só lição 37 existe)
    icons/        → SVGs dos ícones dos grupos
    img/modules/  → imagens dos módulos (Grupo 1 tem imagens, resto não)
    js/           → admin.js, app.js, audio.js, auth.js, dashboard.js, games.js, group.js, recorder.js, vexflow-utils.js
  templates/
    pages/        → todas as páginas da plataforma
    auth/         → login, registro, recuperação de senha
    admin/        → painel do professor
```

---

## Banco de dados (Supabase)

Tabelas existentes com RLS:
- `module_progress` — progresso do aluno por módulo (completed: int)
- `study_days` — dias que o aluno estudou (para streak/heatmap)
- `game_attempts` — tentativas nos jogos
- `submissions` — gravações de áudio enviadas pelo aluno
- `student_access` — módulos liberados pelo professor para cada aluno
- `quiz_answers` — respostas dos quizzes
- `teacher_comments` — comentários do professor por módulo/aluno

---

## Sistema de conteúdo

Módulos são arquivos `.md` com frontmatter YAML + seções markdown:

```
---
number: 1
title: Som e Ruído
group: fundamentos
duration: 15 min
---
## Conceito
...
## Atividade
...
## Quiz
P: Pergunta?
a) Opção A
b) Opção B
*c) Resposta correta
d) Opção D
```

O `md_loader.py` parseia esses arquivos e monta objetos `StudyModule`.

---

## Grupos de estudo (5 grupos)

| # | Nome | Cor | Nível | Módulos |
|---|---|---|---|---|
| 1 | Fundamentos do Som | Dourado #C4943A | Iniciante | ~15 módulos (split/) |
| 2 | Musicalização e Iniciação Musical | Verde #5A8A6A | Iniciante | ~20 módulos |
| 3 | Leitura e Escrita Musical | Roxo #7B5EA7 | Intermediário | ~20 módulos |
| 4 | Teoria Avançada | Azul #4A78B0 | Avançado | ~20 módulos |
| 5 | Método Bona | Laranja #E8632A | Intermediário | 40 lições (números 101–140) |

O Grupo 1 tem redesign completo com imagens e storytelling. Os outros grupos têm conteúdo mas design mais simples.

---

## Método Bona

- 40 lições numeradas 101–140 (bona-licao-01 a bona-licao-40)
- Cada lição tem uma página própria (`bona_module.html`) com iframe do player
- O player (`bona_player.html`) usa OSMD + Tone.js para tocar a partitura MusicXML
- **Problema atual:** só existe o arquivo MusicXML da lição 37. As outras 39 estão faltando.
- No mobile: iframe cresce dinamicamente via postMessage para eliminar scroll interno
- Zoom 0.65 aplicado automaticamente em telas < 640px

---

## Páginas da plataforma

| Rota | Página | Status |
|---|---|---|
| `/` | Landing page pública | ✅ |
| `/home` | Dashboard do aluno | ✅ |
| `/trilhas` | Minhas trilhas (todos os grupos) | ✅ |
| `/grupos` | Visão geral dos grupos | ✅ |
| `/grupos/<slug>` | Página de um grupo | ✅ |
| `/modulos/<slug>` | Módulo de estudo | ✅ |
| `/modulos/bona-licao-XX` | Lição do Método Bona | ✅ |
| `/desempenho` | Estatísticas e gráficos | ✅ |
| `/conquistas` | Medalhas e achievements | ✅ |
| `/aulas` | Aulas extras | ✅ |
| `/jogos` | Games lab | ✅ |
| `/perfil` | Perfil do aluno | ✅ |
| `/configuracoes` | Configurações | ✅ |
| `/admin` | Painel do professor | ✅ |

---

## Gamificação

- **XP:** 50 XP por módulo concluído
- **Nível:** a cada 300 XP sobe de nível (Iniciante → Aprendiz → Estudioso → Dedicado → Músico → Virtuose → Maestro → Lenda)
- **Streak:** dias consecutivos de acesso
- **Conquistas:** 12 achievements baseados em módulos concluídos, streak, grupos completos
- **Missões diárias:** 3 missões fixas (acessar, concluir módulo, manter streak)

---

## Responsividade mobile

- Sidebar vira bottom nav em telas < 768px (base_app.html)
- Todas as páginas têm CSS de media query com `!important` para sobrescrever inline styles
- Trilhas: expand/collapse de grupos no mobile
- Bona: zoom 0.65 + iframe auto-resize via postMessage

---

## Acesso de alunos

- Professor loga no admin e libera módulos individualmente para cada aluno (tabela `student_access`)
- Módulos não liberados aparecem com cadeado
- Professor tem flag `isTeacher: true` que dá acesso a tudo
- Auth via Supabase, sessão mantida no Flask com JWT

---

## O que está faltando / pendente

| Item | Prioridade |
|---|---|
| MusicXML das 39 lições Bona restantes | Alta |
| Módulos Pozzoli (m205–m212, 8 arquivos .md) | Média |
| Rota `/grupos` listando todos os grupos | Média |
| Env vars no CI/CD (SUPABASE_URL etc no Cloud Run) | Alta — sem isso o deploy não funciona |
| Imagens dos módulos (Grupos 2–5) | Baixa |

---

## Decisões de design importantes

- **Inline styles predominantes** — Tailwind é usado mas a maioria do estilo é inline. Media queries usam classes adicionadas via CSS com `!important` para sobrescrever.
- **Sem mock no banco** — Testes devem bater no banco real (sem mock de Supabase).
- **Conteúdo em .md** — Todo conteúdo pedagógico fica em arquivos Markdown, não em banco de dados.
- **iframe para o player Bona** — Isolado em iframe para evitar conflito do Tailwind com o OSMD.
- **PDFs de referência** — Migrados para Supabase Storage (bucket `books`), não servidos pelo Flask.

---

## Paleta de cores

```
Dourado principal:  #C4943A
Dourado claro:      #E8C77A
Fundo bege:         #F2EAD8 / #FAF7F2
Texto escuro:       #2A2419
Verde (concluído):  #5A8A6A
Roxo:               #7B5EA7
Azul:               #4A78B0
Laranja:            #E8632A
Fonte título:       Fraunces (serif, Google Fonts)
```

---

*Gerado em 2026-05-07. Branch principal: `main`. Branch de desenvolvimento atual: `fix_another_things`.*
