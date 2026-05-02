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
  ui.stageActivity.innerHTML = "";

  if (step.kind === "theory") {
    renderReadingActivity(step);
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

function renderTextBlock(text) {
  return text
    .split("\n\n")
    .filter(Boolean)
    .map((paragraph) => `<p>${paragraph}</p>`)
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

function renderVideoStep(step) {
  ui.stageBody.innerHTML = "";
  ui.stageActivity.innerHTML = `
    <div class="video-wrapper">
      <iframe
        src="${step.body}"
        title="${step.title}"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
      ></iframe>
    </div>
    <p class="video-prompt">${step.prompt}</p>
  `;
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
  const client = window.auth?.client;
  const user   = window.auth?.getUser();
  if (!client || !user) return;
  const token = window.auth.session?.access_token;
  if (!token) return;
  fetch(`${client.supabaseUrl}/rest/v1/quiz_answers`, {
    method: "POST",
    headers: {
      "apikey":        client.supabaseKey,
      "Authorization": `Bearer ${token}`,
      "Content-Type":  "application/json",
      "Prefer":        "return=minimal",
    },
    body: JSON.stringify({
      user_id:     user.id,
      module_slug: state.module.slug,
      step_index:  state.activeIndex,
      step_kind:   step.kind,
      question:    step.prompt,
      answer,
      correct,
    }),
  });
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
  const client = window.auth?.client;
  const user   = window.auth?.getUser();
  if (!client || !user) return;

  const token = window.auth.session?.access_token;
  if (!token) return;

  const res = await fetch(
    `${client.supabaseUrl}/rest/v1/teacher_comments` +
    `?student_id=eq.${user.id}&module_slug=eq.${state.module.slug}&order=created_at.asc`,
    {
      headers: {
        "apikey":        client.supabaseKey,
        "Authorization": `Bearer ${token}`,
      },
    }
  );

  if (!res.ok) return;
  const comments = await res.json();
  renderTeacherComments(comments);
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
        <a class="action primary" href="/">Voltar ao início</a>
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
