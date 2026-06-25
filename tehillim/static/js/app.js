const state = {
  module: null,
  activeIndex: 0,
  completed: 0,
};

const ui = {
  path: document.querySelector("#study-path"),
  stageKind: document.querySelector("#stage-kind"),
  stageTitle: document.querySelector("#stage-title"),
  stageSummary: document.querySelector("#stage-summary"),
  stageBody: document.querySelector("#stage-body"),
  stageActivity: document.querySelector("#stage-activity"),
  stageFeedback: document.querySelector("#stage-feedback"),
  completeStep: document.querySelector("#complete-step"),
  resetModule: document.querySelector("#reset-module"),
  progressLabel: document.querySelector("#progress-label"),
  progressBar: document.querySelector("#progress-bar"),
};

const kindLabels = {
  theory: "Teoria",
  video: "Vídeo",
  visual: "Visualização",
  "exercise-mc": "Múltipla Escolha",
  "exercise-tf": "Verdadeiro ou Falso",
  "exercise-fill": "Completar",
  "exercise-match": "Associação",
  "game-memory": "Jogo de Memória",
  "game-challenge": "Desafio Final",
  "game-listen": "Jogo de Escuta",
  "game-drag": "Arrastar e Soltar",
  "game-sort": "Ordenar",
  "game-quiz": "Quiz Dinâmico",
  "game-build": "Construir",
  "game-match": "Associar",
};

function storageKey() {
  return `tehillim:${state.module.slug}:completed`;
}

async function loadModule() {
  const moduleSlug = document.body.dataset.moduleSlug;
  const response = await fetch(`/api/modules/${moduleSlug}`);

  if (!response.ok) {
    throw new Error("Não foi possível carregar o módulo.");
  }

  state.module = await response.json();
  state.completed = Number(localStorage.getItem(storageKey()) || "0");
  state.activeIndex = Math.min(state.completed, state.module.steps.length - 1);
}

function isUnlocked(index) {
  return index <= state.completed;
}

function activeStep() {
  return state.module.steps[state.activeIndex];
}

function renderPath() {
  ui.path.innerHTML = "";

  state.module.steps.forEach((step, index) => {
    const button = document.createElement("button");
    button.className = "path-node";
    button.classList.toggle("active", index === state.activeIndex);
    button.classList.toggle("done", index < state.completed);
    button.disabled = !isUnlocked(index);
    button.innerHTML = `
      <span>${index + 1}</span>
      <strong>${step.title}</strong>
      <small>${kindLabels[step.kind]}</small>
    `;
    button.addEventListener("click", () => {
      state.activeIndex = index;
      clearFeedback();
      render();
    });
    ui.path.appendChild(button);
  });
}

function renderProgress() {
  const total = state.module.steps.length;
  const done = Math.min(state.completed, total);
  ui.progressLabel.textContent = `${done} de ${total}`;
  ui.progressBar.style.width = `${(done / total) * 100}%`;
}

function renderStage() {
  const step = activeStep();
  ui.stageKind.textContent = kindLabels[step.kind];
  ui.stageTitle.textContent = step.title;
  ui.stageSummary.textContent = step.summary;
  ui.stageBody.innerHTML = renderTextBlock(step.body);
  ui.stageBody.style.display = "";   // reset hidden state from DB games
  ui.stageActivity.innerHTML = "";

  if (step.kind === "theory") {
    renderReadingActivity(step);
    renderTTSControls(step.body, step.theory_audio_url || "");
  }

  if (step.kind === "video") {
    renderVideoStep(step);
  }

  if (step.kind === "visual") {
    renderVisualActivity(step);
  }

  if (step.kind === "exercise-mc" || step.kind === "exercise-tf" || step.kind === "exercise-fill") {
    renderChoiceExercise(step);
  }

  if (step.kind === "exercise-match") {
    renderMatchExercise(step);
  }

  // DB games with structured game_data → use rich games.js renderers
  if (step.game_data && typeof step.game_data === "object" && Object.keys(step.game_data).length > 0) {
    if (typeof RENDERERS !== "undefined" && RENDERERS[step.kind]) {
      // Hide the stage-body text (not needed — the game is self-contained)
      ui.stageBody.style.display = "none";

      ui.stageActivity.innerHTML = `
        <div style="background:#F8F7FF;border:1.5px solid #E5E7EB;border-radius:14px;padding:20px 22px;">
          <div class="game-body" id="game-body"></div>
          <div id="game-feedback-inline" style="min-height:18px;margin-top:12px;font-size:13px;font-weight:600;"></div>
        </div>`;

      const el = ui.stageActivity.querySelector("#game-body");

      // Wire globals before renderer so click handlers work immediately
      window.markComplete = () => {
        ui.completeStep.disabled = false;
        ui.completeStep.focus();
      };
      window.setFeedback = (msg, cls) => {
        const fb = document.getElementById("game-feedback-inline");
        if (fb) {
          fb.textContent = msg;
          fb.style.color = cls === "ok" ? "#2e9f65" : cls === "no" ? "#ff8a7a" : "#6B7280";
        }
        ui.stageFeedback.textContent = msg;
        ui.stageFeedback.className   = cls ? `feedback ${cls}` : "feedback";
      };

      RENDERERS[step.kind](step, el);
      return;
    }
  }

  if (step.kind === "game-memory") {
    renderMemoryGame(step);
  }

  if (step.kind === "game-challenge") {
    renderChallengeGame(step);
  }

  const interactiveKinds = ["game-listen", "game-drag", "game-sort", "game-quiz", "game-build", "game-match"];
  if (interactiveKinds.includes(step.kind)) {
    renderInteractiveGame(step);
  }
}

function renderInlineMarkdown(text) {
  return text
    .replace(/==(.+?)==/g, "<mark>$1</mark>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/_(.+?)_/g, "<em>$1</em>");
}

function renderTextBlock(text) {
  return text
    .split("\n\n")
    .filter(Boolean)
    .map((paragraph) => {
      // Image-only paragraph: ![alt](url)
      const imgMatch = paragraph.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
      if (imgMatch) {
        const [, alt, src] = imgMatch;
        return `<img src="${src}" alt="${alt}" style="max-width:380px;width:100%;border-radius:8px;margin:12px auto;display:block;">`;
      }
      return `<p>${renderInlineMarkdown(paragraph)}</p>`;
    })
    .join("");
}

function renderReadingActivity(step) {
  ui.stageActivity.innerHTML = `
    <div class="activity-card">
      <span class="activity-icon">${step.kind === "theory" ? "T" : "V"}</span>
      <p>${step.prompt}</p>
    </div>
  `;
}

function toYouTubeEmbed(url) {
  if (!url) return url;
  if (url.includes("youtube.com/embed/")) return url;
  let m = url.match(/[?&]v=([^&]+)/);
  if (m) return `https://www.youtube.com/embed/${m[1]}`;
  m = url.match(/youtu\.be\/([^?&]+)/);
  if (m) return `https://www.youtube.com/embed/${m[1]}`;
  m = url.match(/youtube\.com\/shorts\/([^?&]+)/);
  if (m) return `https://www.youtube.com/embed/${m[1]}`;
  return url;
}

function toYouTubeId(url) {
  if (!url) return null;
  let m = url.match(/[?&]v=([^&]+)/);
  if (m) return m[1];
  m = url.match(/youtu\.be\/([^?&]+)/);
  if (m) return m[1];
  m = url.match(/youtube\.com\/(?:shorts|embed)\/([^?&]+)/);
  if (m) return m[1];
  return null;
}

function renderVideoStep(step) {
  ui.stageBody.innerHTML = "";
  const embedSrc = toYouTubeEmbed(step.body);
  const videoId  = toYouTubeId(step.body);
  const thumb    = videoId
    ? `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`
    : null;

  const wrapper = document.createElement("div");
  wrapper.className = "video-wrapper";

  if (thumb) {
    wrapper.style.cssText = `background:url('${thumb}') center/cover no-repeat;cursor:pointer;position:relative;`;
    wrapper.innerHTML = `
      <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.25);">
        <svg width="68" height="48" viewBox="0 0 68 48" style="filter:drop-shadow(0 2px 6px rgba(0,0,0,.5))">
          <rect width="68" height="48" rx="12" fill="#FF0000"/>
          <polygon points="26,14 50,24 26,34" fill="#fff"/>
        </svg>
      </div>`;
    wrapper.addEventListener("click", () => {
      wrapper.style.cssText = "";
      wrapper.innerHTML = `<iframe src="${embedSrc}?autoplay=1" title="${step.title}" frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen></iframe>`;
    }, { once: true });
  } else {
    wrapper.innerHTML = `<iframe src="${embedSrc}" title="${step.title}" frameborder="0"
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen></iframe>`;
  }

  ui.stageActivity.innerHTML = "";
  ui.stageActivity.appendChild(wrapper);
  ui.stageActivity.insertAdjacentHTML("beforeend", `<p class="video-prompt">${step.prompt}</p>`);
}

function renderVisualActivity(step) {
  const useVF = step.vf_data && window.VFUtils?.isReady();
  ui.stageActivity.innerHTML = `
    <div class="visual-lab">
      ${useVF
        ? `<div id="module-vf-staff" class="vf-staff-container"></div>`
        : visualFallbackForModule()}
      <div class="activity-card">
        <span class="activity-icon">V</span>
        <p>${step.prompt}</p>
      </div>
    </div>
  `;
  if (useVF) renderVFFromData("module-vf-staff", step.vf_data);
}

function renderVFFromData(id, d) {
  if (!d || !window.VFUtils?.isReady()) return;
  switch (d.type) {
    case "blank":           VFUtils.renderBlank(id, { timeSig: d.time_sig ?? "4/4" }); break;
    case "scale":           VFUtils.renderKeys(id, d.keys); break;
    case "rhythm":          VFUtils.renderRhythm(id, d.pattern); break;
    case "figure_showcase": VFUtils.renderFigureShowcase(id, d.figures); break;
  }
}

function visualFallbackForModule() {
  const slug = state.module.slug;

  if (["compasso", "barra-de-compasso"].includes(slug)) {
    return `
      <div class="meter-grid">
        <span>1</span><span>2</span><b>|</b>
        <span>1</span><span>2</span><span>3</span><b>|</b>
        <span>1</span><span>2</span><span>3</span><span>4</span>
      </div>
    `;
  }

  if (slug === "interpretacao") {
    return `
      <div class="expression-scale">
        <span>piano</span>
        <div><i></i></div>
        <span>forte</span>
      </div>
    `;
  }

  return `
    <div class="creation-board">
      <span>som</span>
      <span>silêncio</span>
      <span>som</span>
      <span>ideia</span>
    </div>
  `;
}

function renderChoiceExercise(step) {
  const typeLabel = {
    "exercise-mc": "Múltipla Escolha",
    "exercise-tf": "Verdadeiro ou Falso",
    "exercise-fill": "Complete a frase",
  }[step.kind] || "Exercício";

  const options = step.options
    .map((option) => `<button class="choice option-choice" data-option="${option}">${option}</button>`)
    .join("");

  ui.stageActivity.innerHTML = `
    <div class="quiz-box">
      <small class="exercise-type-label">${typeLabel}</small>
      <h3>${step.prompt}</h3>
      <div class="choices">${options}</div>
    </div>
  `;

  document.querySelectorAll(".option-choice").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".option-choice").forEach((b) => b.classList.remove("selected", "correct", "wrong"));
      const ok = button.dataset.option === step.answer;
      button.classList.add("selected", ok ? "correct" : "wrong");
      ui.stageFeedback.textContent = ok ? "Resposta certa. Pode concluir a etapa." : "Quase. Tente outra opção.";
      ui.stageFeedback.className = `feedback ${ok ? "ok" : "no"}`;
      ui.completeStep.disabled = !ok;
      saveAnswer(step, button.dataset.option, ok);
    });
  });

  ui.completeStep.disabled = true;
}

function renderMatchExercise(step) {
  const pairRows = step.options
    .map((pair) => {
      const [left, right] = pair.split(" → ");
      return `
        <div class="match-row">
          <span class="match-left">${left}</span>
          <span class="match-arrow">→</span>
          <span class="match-right">${right}</span>
        </div>
      `;
    })
    .join("");

  const checks = step.options
    .map((_, index) => `
      <label class="check-row">
        <input type="checkbox" class="match-check" data-index="${index}">
        Entendi o par ${index + 1}
      </label>
    `)
    .join("");

  ui.stageActivity.innerHTML = `
    <div class="match-exercise">
      <small class="exercise-type-label">Associação</small>
      <h3>${step.prompt}</h3>
      <div class="match-pairs">${pairRows}</div>
      <div class="match-confirm">${checks}</div>
    </div>
  `;

  ui.completeStep.disabled = true;
  document.querySelectorAll(".match-check").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const allChecked = [...document.querySelectorAll(".match-check")].every((c) => c.checked);
      ui.completeStep.disabled = !allChecked;
      if (allChecked) {
        ui.stageFeedback.textContent = "Associações conferidas. Pode concluir a etapa.";
        ui.stageFeedback.className = "feedback ok";
      }
    });
  });
}

function renderMemoryGame(step) {
  const topicButtons = state.module.topics
    .map((topic) => `<button class="memory-chip" data-topic="${topic}">${topic}</button>`)
    .join("");

  ui.stageActivity.innerHTML = `
    <div class="memory-game">
      <p>${step.prompt}</p>
      <div class="memory-chips">${topicButtons}</div>
      <small>Clique em todos os tópicos para fixar a memória do módulo.</small>
    </div>
  `;

  ui.completeStep.disabled = true;

  document.querySelectorAll(".memory-chip").forEach((button) => {
    button.addEventListener("click", () => {
      button.classList.add("selected");
      const selected = document.querySelectorAll(".memory-chip.selected").length;
      if (selected === state.module.topics.length) {
        ui.stageFeedback.textContent = "Memória ativada. Agora conclua a etapa.";
        ui.stageFeedback.className = "feedback ok";
        ui.completeStep.disabled = false;
      }
    });
  });
}

function renderChallengeGame(step) {
  const checks = [
    "Li a proposta com atenção",
    "Consegui fazer sem pressa",
    "Consigo explicar o que pratiquei",
  ]
    .map((item, index) => `
      <label class="check-row">
        <input type="checkbox" class="challenge-check" data-index="${index}">
        ${item}
      </label>
    `)
    .join("");

  ui.stageActivity.innerHTML = `
    <div class="challenge-card">
      <span class="activity-icon">2</span>
      <p>${step.body}</p>
      <div class="challenge-checks">${checks}</div>
    </div>
  `;

  if (window.recorder) {
    ui.stageActivity.appendChild(window.recorder.createWidget(state.module.slug));
  }

  ui.completeStep.disabled = true;
  document.querySelectorAll(".challenge-check").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const allChecked = [...document.querySelectorAll(".challenge-check")].every((item) => item.checked);
      ui.completeStep.disabled = !allChecked;
      if (allChecked) {
      ui.stageFeedback.textContent = "Desafio registrado. Você pode concluir o módulo.";
      ui.stageFeedback.className = "feedback ok";
      }
    });
  });
}

function renderInteractiveGame(step) {
  const gameIcons = {
    "game-listen": "🎧",
    "game-drag": "↔",
    "game-sort": "↕",
    "game-quiz": "?",
    "game-build": "★",
    "game-match": "=",
  };
  const icon = gameIcons[step.kind] || "▶";
  const checks = [
    "Li a missão com atenção",
    "Realizei a atividade proposta",
    "Consigo explicar o que aprendi",
  ]
    .map((item, index) => `
      <label class="check-row">
        <input type="checkbox" class="challenge-check" data-index="${index}">
        ${item}
      </label>
    `)
    .join("");

  ui.stageActivity.innerHTML = `
    <div class="challenge-card">
      <span class="activity-icon">${icon}</span>
      <p>${step.body}</p>
      <div class="challenge-checks">${checks}</div>
    </div>
  `;

  if (window.recorder) {
    ui.stageActivity.appendChild(window.recorder.createWidget(state.module.slug));
  }

  ui.completeStep.disabled = true;
  document.querySelectorAll(".challenge-check").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      const allChecked = [...document.querySelectorAll(".challenge-check")].every((item) => item.checked);
      ui.completeStep.disabled = !allChecked;
      if (allChecked) {
        ui.stageFeedback.textContent = "Atividade concluída. Pode avançar!";
        ui.stageFeedback.className = "feedback ok";
      }
    });
  });
}

function saveAnswer(step, answer, correct) {
  if (!window.auth?.isLoggedIn()) return;
  fetch("/api/quiz-answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      module_slug: state.module.slug,
      step_index:  state.activeIndex,
      step_kind:   step.kind,
      question:    step.prompt,
      answer,
      correct,
    }),
  }).catch(() => {});
}

function completeCurrentStep() {
  let message = "Módulo concluído. Excelente percurso.";

  if (state.activeIndex === state.completed) {
    state.completed = Math.min(state.completed + 1, state.module.steps.length);
    localStorage.setItem(storageKey(), String(state.completed));
    window.auth?.saveProgress(state.module.slug, state.completed);
    window.auth?.markStudyDay();
  }

  if (state.completed < state.module.steps.length) {
    state.activeIndex = state.completed;
    message = "Próxima etapa liberada.";
  }

  render();
  ui.stageFeedback.textContent = message;
  ui.stageFeedback.className = "feedback ok";
}

function resetModule() {
  localStorage.removeItem(storageKey());
  state.completed = 0;
  state.activeIndex = 0;
  clearFeedback();
  render();
}

function clearFeedback() {
  ui.stageFeedback.textContent = "";
  ui.stageFeedback.className = "feedback";
  ui.completeStep.disabled = false;
}

function render() {
  renderPath();
  renderProgress();
  renderStage();
}

async function loadTeacherComments() {
  if (!window.auth?.isLoggedIn()) return;
  // Comentários do professor chegam pela aba Mensagens — não exibe mais aqui
}

function renderTeacherComments(comments) {
  let box = document.getElementById("teacher-comments-box");

  if (!comments.length) {
    if (box) box.remove();
    return;
  }

  if (!box) {
    box = document.createElement("aside");
    box.id        = "teacher-comments-box";
    box.className = "teacher-comments-box";
    // Insere depois das actions
    const actions = document.querySelector(".actions");
    actions?.insertAdjacentElement("afterend", box);
  }

  const fmt = (iso) => new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });

  box.innerHTML = `
    <h4 class="tc-title">💬 Feedback do professor</h4>
    ${comments.map((c) => `
      <div class="tc-item">
        <p class="tc-content">${c.content}</p>
        <small class="tc-date">${fmt(c.created_at)}</small>
      </div>
    `).join("")}
  `;
}

function renderLocked(loggedIn = true) {
  const layout = document.querySelector(".study-layout");
  if (!layout) return;
  if (!loggedIn) {
    layout.innerHTML = `
      <div class="module-locked">
        <span class="lock-icon">🔒</span>
        <h2>Faça login para acessar</h2>
        <p>Você precisa estar logado para acessar este módulo.</p>
        <a class="action primary" href="/login">Entrar</a>
      </div>
    `;
  } else {
    layout.innerHTML = `
      <div class="module-locked">
        <span class="lock-icon">🔒</span>
        <h2>Módulo bloqueado</h2>
        <p>Este módulo ainda não foi liberado pelo seu professor. Aguarde a liberação para continuar.</p>
        <a class="action primary" href="/index.html">Voltar ao início</a>
      </div>
    `;
  }
}

async function checkAccess() {
  await Promise.race([
    window.auth?.ready ?? Promise.resolve(),
    new Promise((r) => setTimeout(r, 5000)),
  ]);
  const loggedIn = window.auth?.isLoggedIn() ?? false;
  console.log("[access] loggedIn:", loggedIn);
  if (!loggedIn) return { loggedIn: false, isTeacher: false, slugs: new Set() };
  const access = await window.auth.getAccess();
  console.log("[access] isTeacher:", access.isTeacher, "| slugs:", [...access.slugs]);
  return { loggedIn: true, isTeacher: access.isTeacher, slugs: access.slugs };
}

async function start() {
  if (!document.body.dataset.moduleSlug) return;

  try {
    const cookieAccess = document.body.dataset.accessOk === "true";

    if (cookieAccess) {
      // Servidor já confirmou acesso via cookie — carrega direto, sem esperar auth
      await loadModule();
    } else {
      // Sem cookie — verifica acesso via JS (pode ter delay se JWT expirado)
      const [, { loggedIn, isTeacher, slugs }] = await Promise.all([
        loadModule(),
        checkAccess(),
      ]);
      if (!isTeacher && (!loggedIn || !slugs.has(state.module.slug))) {
        renderLocked(loggedIn);
        return;
      }
    }

    ui.completeStep.addEventListener("click", completeCurrentStep);
    ui.resetModule.addEventListener("click", resetModule);
    render();
    loadTeacherComments();
  } catch (error) {
    if (ui.stageFeedback) {
      ui.stageFeedback.textContent = error.message;
      ui.stageFeedback.className = "feedback no";
    }
  }
}

start();

// ── Text-to-Speech ────────────────────────────────────────────────────────────

let _ttsVoices = [];
let _ttsSelectedVoice = null;
let _ttsSpeaking = false;

function _loadVoices() {
  _ttsVoices = speechSynthesis.getVoices();
  // prefer pt-BR, then pt, then en
  const pt = _ttsVoices.filter(v => v.lang.startsWith("pt"));
  if (pt.length > 0 && !_ttsSelectedVoice) {
    _ttsSelectedVoice = pt[0].name;
  }
}

if (typeof speechSynthesis !== "undefined") {
  _loadVoices();
  speechSynthesis.onvoiceschanged = _loadVoices;
}

function _stripMarkdown(text) {
  return text
    .replace(/!\[.*?\]\(.*?\)/g, "")     // images
    .replace(/\[([^\]]+)\]\(.*?\)/g, "$1") // links
    .replace(/#{1,6}\s/g, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/_(.+?)_/g, "$1")
    .replace(/`(.+?)`/g, "$1")
    .trim();
}

function renderTTSControls(bodyText, audioUrl) {
  document.getElementById("tts-panel")?.remove();

  const panel = document.createElement("div");
  panel.id = "tts-panel";
  panel.style.cssText = "position:absolute;top:20px;right:24px;z-index:10;";

  const btn = document.createElement("button");
  btn.id = "tts-btn";
  btn.style.cssText = [
    "display:flex;align-items:center;gap:7px;",
    "padding:9px 18px;border-radius:12px;",
    "background:#C4943A;color:white;",
    "font-size:13px;font-weight:700;",
    "border:none;cursor:pointer;",
    "box-shadow:0 2px 10px rgba(196,148,58,.35);",
    "transition:background .15s,box-shadow .15s;",
  ].join("");
  btn.onmouseenter = () => { btn.style.background = "#B3852F"; };
  btn.onmouseleave = () => { if (!_ttsSpeaking) btn.style.background = "#C4943A"; };
  btn.innerHTML = `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.536 8.464a5 5 0 010 7.072M12 6a7 7 0 010 12M8.464 8.464a5 5 0 000 7.072"/></svg> Ouvir`;
  btn.onclick = () => _ttsSpeaking ? _ttsStop() : (audioUrl ? _ttsPlayUrl(audioUrl) : _ttsSpeak(bodyText));

  panel.appendChild(btn);

  const stage = document.getElementById("study-stage");
  if (stage) stage.prepend(panel);
}

let _ttsAudioEl = null;
let _ttsAzureVoice = localStorage.getItem("tts_azure_voice") || "pt-BR-FranciscaNeural";

function _ttsSetBtn(state) {
  const btn = document.getElementById("tts-btn");
  if (!btn) return;
  if (state === "loading") {
    btn.innerHTML = `<svg class="spin" width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path d="M4 12a8 8 0 018-8"/></svg> Gerando...`;
    btn.style.background = "#B3852F";
    btn.disabled = true;
  } else if (state === "playing") {
    btn.innerHTML = `<svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg> Parar`;
    btn.style.background = "#8B6020";
    btn.disabled = false;
  } else {
    btn.innerHTML = `<svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.536 8.464a5 5 0 010 7.072M12 6a7 7 0 010 12M8.464 8.464a5 5 0 000 7.072"/></svg> Ouvir`;
    btn.style.background = "#C4943A";
    btn.disabled = false;
  }
}

async function _ttsSpeak(text) {
  const clean = _stripMarkdown(text);

  // Try Azure Neural TTS first
  try {
    _ttsSetBtn("loading");
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: clean, voice: _ttsAzureVoice }),
    });
    if (!res.ok) throw new Error("no_azure");
    const blob = await res.blob();

    if (!_ttsAudioEl) {
      _ttsAudioEl = document.createElement("audio");
      document.body.appendChild(_ttsAudioEl);
    }
    _ttsAudioEl.src = URL.createObjectURL(blob);
    _ttsAudioEl.play();
    _ttsSpeaking = true;
    _ttsSetBtn("playing");
    _ttsAudioEl.onended = () => { _ttsSpeaking = false; _ttsSetBtn("idle"); };
    return;
  } catch(_) {
    // fallback to browser TTS
  }

  // Browser TTS fallback
  if (!("speechSynthesis" in window)) { _ttsSetBtn("idle"); return; }
  speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(clean);
  utter.lang = "pt-BR";
  if (_ttsSelectedVoice) {
    const voice = _ttsVoices.find(v => v.name === _ttsSelectedVoice);
    if (voice) utter.voice = voice;
  }
  utter.rate = 0.95;
  utter.onstart  = () => { _ttsSpeaking = true;  _ttsSetBtn("playing"); };
  utter.onend    = () => { _ttsSpeaking = false;  _ttsSetBtn("idle"); };
  utter.onerror  = () => { _ttsSpeaking = false;  _ttsSetBtn("idle"); };
  speechSynthesis.speak(utter);
}

function _ttsStop() {
  if (_ttsAudioEl) { _ttsAudioEl.pause(); _ttsAudioEl.src = ""; }
  speechSynthesis.cancel();
  _ttsSpeaking = false;
  _ttsSetBtn("idle");
}

function _ttsPlayUrl(url) {
  if (!_ttsAudioEl) {
    _ttsAudioEl = document.createElement("audio");
    document.body.appendChild(_ttsAudioEl);
  }
  _ttsAudioEl.src = url;
  _ttsAudioEl.play();
  _ttsSpeaking = true;
  _ttsSetBtn("playing");
  _ttsAudioEl.onended = () => { _ttsSpeaking = false; _ttsSetBtn("idle"); };
}

function _toggleVoicePanel() {
  const existing = document.getElementById("tts-voice-panel");
  if (existing) { existing.remove(); return; }

  const panel = document.createElement("div");
  panel.id = "tts-voice-panel";
  panel.style.cssText = "position:absolute;background:white;border:1px solid #E5E7EB;border-radius:14px;padding:12px;box-shadow:0 8px 24px rgba(0,0,0,.12);z-index:200;max-height:340px;overflow-y:auto;min-width:260px;";

  const voices = speechSynthesis.getVoices();
  if (voices.length === 0) {
    panel.innerHTML = `<p style="font-size:12px;color:#9CA3AF;padding:8px;">Nenhuma voz disponível no seu navegador.</p>`;
  } else {
    const ptVoices = voices.filter(v => v.lang.startsWith("pt"));
    const otherVoices = voices.filter(v => !v.lang.startsWith("pt"));

    let html = "";
    if (ptVoices.length) {
      html += `<p style="font-size:10px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.08em;margin:0 0 6px;">Português</p>`;
      ptVoices.forEach(v => {
        const active = v.name === _ttsSelectedVoice ? "background:#FBF6EE;color:#C4943A;font-weight:600;" : "";
        html += `<button onclick="window._ttsSelectVoice('${v.name.replace(/'/g,"\\'")}',this)" style="display:block;width:100%;text-align:left;padding:7px 10px;border-radius:8px;border:none;font-size:12px;cursor:pointer;${active}">${v.name} <span style="font-size:10px;color:#9CA3AF;">(${v.lang})</span></button>`;
      });
    }
    if (otherVoices.length) {
      html += `<p style="font-size:10px;font-weight:700;color:#9CA3AF;text-transform:uppercase;letter-spacing:.08em;margin:10px 0 6px;">Outras línguas</p>`;
      otherVoices.forEach(v => {
        const active = v.name === _ttsSelectedVoice ? "background:#FBF6EE;color:#C4943A;font-weight:600;" : "";
        html += `<button onclick="window._ttsSelectVoice('${v.name.replace(/'/g,"\\'")}',this)" style="display:block;width:100%;text-align:left;padding:7px 10px;border-radius:8px;border:none;font-size:12px;cursor:pointer;${active}">${v.name} <span style="font-size:10px;color:#9CA3AF;">(${v.lang})</span></button>`;
      });
    }
    panel.innerHTML = html;
  }

  const voiceBtn = document.getElementById("tts-voice-btn");
  if (voiceBtn) {
    voiceBtn.style.position = "relative";
    voiceBtn.appendChild(panel);
  }

  // close on outside click
  setTimeout(() => {
    document.addEventListener("click", function _close() {
      document.getElementById("tts-voice-panel")?.remove();
      document.removeEventListener("click", _close);
    });
  }, 0);
}

window._ttsSelectVoice = function(name, btn) {
  _ttsSelectedVoice = name;
  if (name.startsWith("pt-BR-")) {
    _ttsAzureVoice = name;
    localStorage.setItem("tts_azure_voice", name);
    const shortName = name.replace("pt-BR-","").replace("Neural","");
    const vBtn = document.getElementById("tts-voice-btn");
    if (vBtn) vBtn.innerHTML = `🎙 ${shortName}`;
  }
  btn.closest("#tts-voice-panel")?.querySelectorAll("button").forEach(b => {
    b.style.background = ""; b.style.color = ""; b.style.fontWeight = "";
  });
  btn.style.background = "#FBF6EE"; btn.style.color = "#C4943A"; btn.style.fontWeight = "600";
  document.getElementById("tts-voice-panel")?.remove();
};
