// ─── State ────────────────────────────────────────────────────────────────────

const lab = { games: [], active: null, completed: new Set() };

// ─── Bootstrap ────────────────────────────────────────────────────────────────

async function init() {
  try {
    const res = await fetch("/api/games/demo");
    const data = await res.json();
    lab.games = data.games;
    document.getElementById("lab-count").textContent = `${lab.games.length} jogos disponíveis.`;
    renderNav();
    if (lab.games.length) activate(lab.games[0].kind);
  } catch (e) {
    document.getElementById("lab-stage").innerHTML = "<p>Erro ao carregar jogos.</p>";
  }
}

// ─── Nav ──────────────────────────────────────────────────────────────────────

function renderNav() {
  const nav = document.getElementById("lab-nav");
  const cats = {};
  lab.games.forEach((g) => {
    if (!cats[g.category]) cats[g.category] = [];
    cats[g.category].push(g);
  });

  nav.innerHTML = Object.entries(cats)
    .map(
      ([cat, games]) => `
      <div class="nav-group">
        <p class="nav-category">${cat}</p>
        ${games.map((g) => `<button class="nav-item" data-kind="${g.kind}">${g.title}</button>`).join("")}
      </div>
    `
    )
    .join("");

  nav.addEventListener("click", (e) => {
    const btn = e.target.closest(".nav-item");
    if (btn) activate(btn.dataset.kind);
  });
}

function activate(kind) {
  lab.active = kind;
  document.querySelectorAll(".nav-item").forEach((el) =>
    el.classList.toggle("active", el.dataset.kind === kind)
  );
  const game = lab.games.find((g) => g.kind === kind);
  if (game) renderStage(game);
}

// ─── Stage ────────────────────────────────────────────────────────────────────

function renderStage(game) {
  const stage = document.getElementById("lab-stage");
  stage.innerHTML = `
    <div class="game-header">
      <span class="game-kind-badge">${game.kind}</span>
      <h2>${game.title}</h2>
      <p class="game-description">${game.description}</p>
    </div>
    <div class="game-body" id="game-body"></div>
    <p class="game-feedback" id="gfeedback"></p>
    <button class="complete-btn" id="complete-btn">Concluir etapa →</button>
  `;

  document.getElementById("complete-btn").addEventListener("click", () => {
    const idx = lab.games.findIndex((g) => g.kind === game.kind);
    if (idx < lab.games.length - 1) activate(lab.games[idx + 1].kind);
  });

  const body = document.getElementById("game-body");
  const renderer = RENDERERS[game.kind];
  if (renderer) renderer(game, body);
  else body.innerHTML = `<p>Renderer não implementado para <code>${game.kind}</code>.</p>`;
}

function markComplete() {
  if (!lab.active) return;
  lab.completed.add(lab.active);
  const navItem = document.querySelector(`.nav-item[data-kind="${lab.active}"]`);
  if (navItem) navItem.classList.add("done");
  const btn = document.getElementById("complete-btn");
  if (btn) btn.classList.add("visible");
}

function setFeedback(text, type) {
  const fb = document.getElementById("gfeedback");
  if (!fb) return;
  fb.textContent = text;
  fb.className = `game-feedback ${type}`;
  if (text && type === "ok") window.audio?.correct();
  if (text && type === "no") window.audio?.wrong();
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function _resultHtml(correct, total) {
  const pct = total > 0 ? correct / total : 0;
  const stars = pct === 1 ? "⭐⭐⭐" : pct >= 0.7 ? "⭐⭐" : pct >= 0.4 ? "⭐" : "";
  const msg = pct === 1 ? "Perfeito! Mandou muito bem!" : pct >= 0.7 ? "Muito bom! Quase lá!" : "Continue praticando, você vai conseguir!";
  const color = pct >= 0.7 ? "var(--green)" : "var(--coral)";
  return `
    <div class="tf-result" style="text-align:center;">
      <div style="font-size:2rem;margin-bottom:4px;">${stars || "🎯"}</div>
      <strong style="color:${color};font-size:1.6rem;">${correct} de ${total}</strong>
      <p style="margin-top:6px;color:#5a6a7a;">${msg}</p>
    </div>`;
}

function shuffle(arr) {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ─── Renderers ────────────────────────────────────────────────────────────────

const RENDERERS = {
  "game-word-select": renderWordSelect,
  "game-fill-sentence": renderFillSentence,
  "game-unscramble": renderUnscramble,
  "game-find-error": renderFindError,
  "game-crossword": renderCrossword,
  "game-connect": renderConnect,
  "game-puzzle": renderPuzzle,
  "game-sequence": renderSequence,
  "game-chart-fill": renderChartFill,
  "game-speedrun": renderSpeedrun,
  "game-true-false-rapid": renderTrueFalseRapid,
  "game-hot-cold": renderHotCold,
  "game-rhythm-tap": renderRhythmTap,
  "game-compose": renderCompose,
  "game-teach": renderTeach,
  "game-memory": renderMemory,
  "game-arrange": renderArrange,
  "game-sort": renderArrange,
  "game-quiz": renderQuiz,
  "game-drag": renderDragDrop,
  "game-build": renderBuild,
  "game-challenge": renderChallenge,
};

// ── game-word-select ──────────────────────────────────────────────────────────

function renderWordSelect(game, el) {
  const { parts } = game.game_data;
  const html = parts
    .map((p) =>
      p.clickable
        ? `<button class="word-btn" data-correct="${p.correct}">${p.text}</button>`
        : `<span>${p.text}</span>`
    )
    .join("");

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <p class="word-sentence">${html}</p>
  `;

  el.querySelectorAll(".word-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      el.querySelectorAll(".word-btn").forEach((b) => b.classList.remove("correct", "wrong"));
      const ok = btn.dataset.correct === "true";
      btn.classList.add(ok ? "correct" : "wrong");
      setFeedback(ok ? "Correto! Essa é a palavra certa." : "Não é essa. Tente outra.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  });
}

// ── game-fill-sentence ────────────────────────────────────────────────────────

function renderFillSentence(game, el) {
  const { before, after, options, answer } = game.game_data;
  const opts = options.map((o) => `<button class="choice" data-value="${o}">${o}</button>`).join("");

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <p class="fill-sentence">${before}<span class="fill-blank" id="fill-blank">___</span>${after}</p>
    <div class="choices">${opts}</div>
  `;

  el.querySelectorAll(".choice").forEach((btn) => {
    btn.addEventListener("click", () => {
      el.querySelectorAll(".choice").forEach((b) => b.classList.remove("correct", "wrong"));
      const ok = btn.dataset.value === answer;
      btn.classList.add(ok ? "correct" : "wrong");
      const blank = document.getElementById("fill-blank");
      blank.textContent = btn.dataset.value;
      blank.className = `fill-blank ${ok ? "filled-ok" : "filled-no"}`;
      setFeedback(ok ? "Correto!" : "Tente outra palavra.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  });
}

// ── game-unscramble ───────────────────────────────────────────────────────────

function renderUnscramble(game, el) {
  const { shuffled, solution } = game.game_data;
  let chosen = [];

  const draw = () => {
    const usedIndices = chosen.map((c) => c.si);
    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="unscramble-answer">
        ${
          chosen.length
            ? chosen.map((c, i) => `<button class="word-chip placed" data-ci="${i}">${c.word}</button>`).join("")
            : '<span class="placeholder-text">Clique nas palavras abaixo para montar a frase</span>'
        }
      </div>
      <div class="unscramble-pool">
        ${shuffled
          .map((w, i) =>
            usedIndices.includes(i)
              ? `<span class="word-chip used">${w}</span>`
              : `<button class="word-chip" data-si="${i}">${w}</button>`
          )
          .join("")}
      </div>
      <button class="secondary-btn" id="undo-btn">← Desfazer</button>
    `;

    el.querySelectorAll(".unscramble-pool .word-chip:not(.used)").forEach((btn) => {
      btn.addEventListener("click", () => {
        chosen.push({ si: Number(btn.dataset.si), word: shuffled[Number(btn.dataset.si)] });
        draw();
        if (chosen.length === solution.length) {
          const ok = chosen.every((c, i) => c.word === solution[i]);
          setFeedback(ok ? "Perfeito! Frase montada corretamente." : "Quase! Verifique a ordem.", ok ? "ok" : "no");
          if (ok) markComplete();
        }
      });
    });

    el.querySelectorAll(".word-chip.placed").forEach((btn) => {
      btn.addEventListener("click", () => {
        chosen.splice(Number(btn.dataset.ci), 1);
        draw();
        setFeedback("", "");
      });
    });

    el.querySelector("#undo-btn").addEventListener("click", () => {
      chosen.pop();
      draw();
      setFeedback("", "");
    });
  };

  draw();
}

// ── game-find-error ───────────────────────────────────────────────────────────

function renderFindError(game, el) {
  const { parts } = game.game_data;
  const html = parts
    .map((p, i) =>
      p.error
        ? `<button class="error-part" data-error="true" data-idx="${i}">${p.text}</button>`
        : `<button class="error-part" data-error="false" data-idx="${i}">${p.text}</button>`
    )
    .join("");

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <div class="error-sentence">${html}</div>
  `;

  el.querySelectorAll(".error-part").forEach((btn) => {
    btn.addEventListener("click", () => {
      el.querySelectorAll(".error-part").forEach((b) => b.classList.remove("correct-pick", "wrong-pick"));
      const ok = btn.dataset.error === "true";
      btn.classList.add(ok ? "correct-pick" : "wrong-pick");
      setFeedback(ok ? "Correto! Esse é o termo errado." : "Não é esse. Continue procurando.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  });
}

// ── game-crossword ────────────────────────────────────────────────────────────

function renderCrossword(game, el) {
  const { clues } = game.game_data;

  const wordsHtml = clues
    .map(
      (c, i) => `
      <div class="crossword-word">
        <div class="crossword-meta">
          <span class="crossword-num">${i + 1}</span>
          <span>${c.direction} — ${c.clue}</span>
        </div>
        <div class="letter-inputs" data-word-idx="${i}" data-answer="${c.answer}">
          ${c.answer
            .split("")
            .map(() => `<input maxlength="1" autocomplete="off">`)
            .join("")}
        </div>
      </div>
    `
    )
    .join("");

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <div class="crossword-list">${wordsHtml}</div>
    <button class="secondary-btn" id="check-crossword" style="margin-top:16px">Verificar</button>
  `;

  el.querySelectorAll(".letter-inputs input").forEach((input, _, all) => {
    input.addEventListener("input", () => {
      input.value = input.value.toUpperCase().slice(-1);
      const parent = input.closest(".letter-inputs");
      const inputs = [...parent.querySelectorAll("input")];
      const idx = inputs.indexOf(input);
      if (input.value && idx < inputs.length - 1) inputs[idx + 1].focus();
    });
    input.addEventListener("keydown", (e) => {
      if (e.key === "Backspace" && !input.value) {
        const parent = input.closest(".letter-inputs");
        const inputs = [...parent.querySelectorAll("input")];
        const idx = inputs.indexOf(input);
        if (idx > 0) { inputs[idx - 1].value = ""; inputs[idx - 1].focus(); }
      }
    });
  });

  el.querySelector("#check-crossword").addEventListener("click", () => {
    let allCorrect = true;
    el.querySelectorAll(".letter-inputs").forEach((group) => {
      const answer = group.dataset.answer;
      const inputs = [...group.querySelectorAll("input")];
      const typed = inputs.map((i) => i.value).join("");
      const ok = typed === answer;
      if (!ok) allCorrect = false;
      inputs.forEach((input, i) => {
        input.className = typed[i] === answer[i] ? "letter-ok" : "letter-no";
      });
    });
    setFeedback(allCorrect ? "Todas as palavras corretas!" : "Verifique as letras marcadas em vermelho.", allCorrect ? "ok" : "no");
    if (allCorrect) markComplete();
  });
}

// ── game-connect (ligar pontos) ───────────────────────────────────────────────

function renderConnect(game, el) {
  const { left, right_shuffled: right, pairs } = game.game_data;
  let selectedLeft = null;
  const connections = {};
  const pairColors = ["0", "1", "2", "3", "4"];

  const draw = () => {
    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="connect-board">
        <div class="connect-col" id="col-left">
          ${left
            .map(
              (item, i) => `
            <div class="connect-item" data-side="left" data-idx="${i}"
              ${connections[i] !== undefined ? `data-pair="${pairColors[i]}"` : ""}
              ${selectedLeft === i ? 'class="connect-item selected"' : 'class="connect-item"'}>
              ${item}
            </div>`
            )
            .join("")}
        </div>
        <div class="connect-lines">
          ${left.map(() => `<div class="connect-dot"></div>`).join("")}
        </div>
        <div class="connect-col" id="col-right">
          ${right
            .map((item, i) => {
              const connectedLeftIdx = Object.entries(connections).find(([, ri]) => ri === i)?.[0];
              return `
              <div class="connect-item" data-side="right" data-idx="${i}"
                ${connectedLeftIdx !== undefined ? `data-pair="${pairColors[Number(connectedLeftIdx)]}"` : ''}
                class="connect-item">
                ${item}
              </div>`;
            })
            .join("")}
        </div>
      </div>
    `;

    el.querySelectorAll(".connect-item[data-side='left']").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedLeft = Number(btn.dataset.idx);
        draw();
      });
    });

    el.querySelectorAll(".connect-item[data-side='right']").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (selectedLeft === null) return;
        connections[selectedLeft] = Number(btn.dataset.idx);
        selectedLeft = null;
        draw();
        checkConnect(pairs, left, right, connections);
      });
    });
  };

  draw();
}

function checkConnect(pairs, left, right, connections) {
  if (Object.keys(connections).length < left.length) return;
  const ok = left.every((item, li) => {
    const ri = connections[li];
    return ri !== undefined && right[ri] === pairs[item];
  });
  setFeedback(ok ? "Perfeito! Todos os pares corretos." : "Algum par está errado. Tente de novo.", ok ? "ok" : "no");
  if (ok) markComplete();
}

// ── game-puzzle ───────────────────────────────────────────────────────────────

function renderPuzzle(game, el) {
  const { slots, pieces_shuffled, solution } = game.game_data;
  let placed = Array(slots.length).fill(null);
  let selectedPiece = null;

  const draw = () => {
    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="puzzle-board">
        <div class="puzzle-slots">
          ${slots
            .map(
              (label, i) => `
            <div class="puzzle-slot ${placed[i] ? "has-piece" : ""}" data-slot-idx="${i}">
              <span class="slot-label">${label}</span>
              ${placed[i] ? `<span class="slot-piece">${placed[i]}</span>` : ""}
            </div>`
            )
            .join("")}
        </div>
        <div class="puzzle-pieces">
          ${pieces_shuffled
            .map((piece) => {
              const isUsed = placed.includes(piece);
              const isSelected = selectedPiece === piece;
              return `<button class="puzzle-piece ${isUsed ? "used" : ""} ${isSelected ? "selected" : ""}" data-piece="${piece}">${piece}</button>`;
            })
            .join("")}
        </div>
        <button class="secondary-btn" id="check-puzzle">Verificar</button>
      </div>
    `;

    el.querySelectorAll(".puzzle-piece:not(.used)").forEach((btn) => {
      btn.addEventListener("click", () => {
        selectedPiece = btn.dataset.piece;
        draw();
      });
    });

    el.querySelectorAll(".puzzle-slot").forEach((slot) => {
      slot.addEventListener("click", () => {
        if (!selectedPiece) return;
        placed[Number(slot.dataset.slotIdx)] = selectedPiece;
        selectedPiece = null;
        draw();
      });
    });

    el.querySelector("#check-puzzle").addEventListener("click", () => {
      const ok = placed.every((p, i) => p === solution[i]);
      el.querySelectorAll(".puzzle-slot").forEach((slot, i) => {
        if (!placed[i]) return;
        slot.classList.toggle("correct", placed[i] === solution[i]);
        slot.classList.toggle("wrong", placed[i] !== solution[i]);
      });
      setFeedback(ok ? "Perfeito! Ordem correta." : "Alguma peça está no lugar errado.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  };

  draw();
}

// ── game-sequence ─────────────────────────────────────────────────────────────

function renderSequence(game, el) {
  const { items, blank_index, options, answer } = game.game_data;
  const blankAt = blank_index ?? items.findIndex((it) => it === "?");

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <p style="font-size:12px;color:#9CA3AF;margin-bottom:8px">Qual item completa a sequência no lugar do <strong>?</strong>?</p>
    <div class="sequence-strip">
      ${items
        .map((item, i) => {
          const isBlank = i === blankAt;
          const node = isBlank
            ? `<div class="seq-blank" id="seq-blank">?</div>`
            : `<div class="seq-item">${item}</div>`;
          const arrow = i < items.length - 1 ? `<span class="seq-arrow">→</span>` : "";
          return node + arrow;
        })
        .join("")}
    </div>
    <button class="secondary-btn" id="play-seq" style="margin-bottom:14px">▶ Ouvir sequência</button>
    <div class="choices">
      ${options.map((o) => `<button class="choice" data-value="${o}">${o}</button>`).join("")}
    </div>
  `;

  el.querySelector("#play-seq").addEventListener("click", () => {
    window.audio?.playSequenceWithGap(items);
  });

  el.querySelectorAll(".choice").forEach((btn) => {
    btn.addEventListener("click", () => {
      el.querySelectorAll(".choice").forEach((b) => b.classList.remove("correct", "wrong"));
      const ok = btn.dataset.value === answer;
      btn.classList.add(ok ? "correct" : "wrong");
      const blank = document.getElementById("seq-blank");
      blank.textContent = btn.dataset.value;
      blank.className = `seq-blank ${ok ? "filled-ok" : "filled-no"}`;
      setFeedback(ok ? "Correto!" : "Não é essa nota. Tente outra.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  });
}

// ── game-chart-fill ───────────────────────────────────────────────────────────

function renderChartFill(game, el) {
  const { note, positions } = game.game_data;
  const staffId = "chart-fill-staff";

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <p style="font-size:0.9rem;color:#5a6a7a;margin-bottom:8px">Nota: <strong>${note}</strong></p>
    <div id="${staffId}" class="vf-staff-container"></div>
    <div class="staff-positions">
      ${positions.map((p, i) => `
        <button class="staff-pos-btn" data-correct="${p.correct}" data-idx="${i}" data-vf-key="${p.vf_key || ''}">
          ${p.label}
        </button>`).join("")}
    </div>
  `;

  if (window.VFUtils?.isReady()) {
    window.VFUtils.renderBlank(staffId, { timeSig: null });
  }

  el.querySelectorAll(".staff-pos-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      el.querySelectorAll(".staff-pos-btn").forEach((b) => b.classList.remove("correct", "wrong"));
      const ok = btn.dataset.correct === "true";
      btn.classList.add(ok ? "correct" : "wrong");
      if (ok && btn.dataset.vfKey && window.VFUtils?.isReady()) {
        window.VFUtils.renderNote(staffId, btn.dataset.vfKey, "w");
      }
      setFeedback(ok ? "Correto! É essa a posição." : "Não é essa. Tente outra posição.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  });
}

// ── game-speedrun ─────────────────────────────────────────────────────────────

function renderSpeedrun(game, el) {
  const { time_limit, questions } = game.game_data;
  let qIdx = 0, score = 0, timer = null;

  const drawQuestion = () => {
    if (qIdx >= questions.length) { endSpeedrun(); return; }
    const q = questions[qIdx];
    el.querySelector("#sr-question").textContent = q.prompt;
    el.querySelector("#sr-options").innerHTML = q.options
      .map((o) => `<button class="choice" data-value="${o}">${o}</button>`)
      .join("");
    el.querySelector("#sr-count").textContent = `${qIdx + 1}/${questions.length}`;

    el.querySelectorAll(".choice").forEach((btn) => {
      btn.addEventListener("click", () => {
        if (btn.dataset.value === q.answer) score++;
        qIdx++;
        drawQuestion();
      });
    });
  };

  const endSpeedrun = () => {
    clearInterval(timer);
    el.innerHTML = `
      <p class="game-prompt">Tempo encerrado!</p>
      ${_resultHtml(score, questions.length)}
    `;
    const ok = score >= questions.length * 0.7;
    setFeedback(ok ? "Ótimo desempenho!" : "Pratique mais e tente novamente.", ok ? "ok" : "no");
    if (score >= questions.length * 0.5) markComplete();
  };

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <div class="speedrun-header">
      <span class="speedrun-timer" id="sr-timer">${time_limit}</span>
      <span class="speedrun-score" id="sr-count">—</span>
    </div>
    <div id="sr-body">
      <button class="start-btn" id="sr-start">▶ Iniciar</button>
    </div>
  `;

  el.querySelector("#sr-start").addEventListener("click", () => {
    let remaining = time_limit;
    el.querySelector("#sr-body").innerHTML = `
      <p class="speedrun-question" id="sr-question">...</p>
      <div class="choices" id="sr-options"></div>
    `;
    el.querySelector("#sr-count").textContent = `${qIdx + 1}/${questions.length}`;
    drawQuestion();

    timer = setInterval(() => {
      remaining--;
      const timerEl = el.querySelector("#sr-timer");
      timerEl.textContent = remaining;
      if (remaining <= 5) timerEl.classList.add("urgent");
      if (remaining <= 0) endSpeedrun();
    }, 1000);
  });
}

// ── game-true-false-rapid ─────────────────────────────────────────────────────

function renderTrueFalseRapid(game, el) {
  const { statements } = game.game_data;
  let idx = 0;
  const results = [];

  const draw = () => {
    if (idx >= statements.length) { showResults(); return; }
    const s = statements[idx];
    const dots = statements
      .map((_, i) => {
        const cls = i < idx ? (results[i] ? "ok" : "no") : i === idx ? "cur" : "";
        return `<div class="tf-dot ${cls}"></div>`;
      })
      .join("");

    el.innerHTML = `
      <div class="tf-progress">${dots}</div>
      <div class="tf-statement">${s.text}</div>
      <div class="tf-buttons">
        <button class="tf-btn tf-btn-v" id="btn-v">Verdadeiro</button>
        <button class="tf-btn tf-btn-f" id="btn-f">Falso</button>
      </div>
    `;

    const handle = (chosen) => {
      results.push(chosen === s.answer);
      idx++;
      draw();
    };
    el.querySelector("#btn-v").addEventListener("click", () => handle("Verdadeiro"));
    el.querySelector("#btn-f").addEventListener("click", () => handle("Falso"));
  };

  const showResults = () => {
    const correct = results.filter(Boolean).length;
    const dots = results.map((ok) => `<div class="tf-dot ${ok ? "ok" : "no"}"></div>`).join("");
    el.innerHTML = `
      <div class="tf-progress">${dots}</div>
      ${_resultHtml(correct, statements.length)}
    `;
    const ok = correct >= statements.length * 0.7;
    setFeedback(ok ? "Bom desempenho!" : "Revise o conteúdo.", ok ? "ok" : "no");
    if (ok) markComplete();
  };

  draw();
}

// ── game-hot-cold ─────────────────────────────────────────────────────────────

function renderHotCold(game, el) {
  const { answer, hints } = game.game_data;
  let revealed = 0;

  const draw = () => {
    const hintsHtml = hints
      .slice(0, revealed)
      .map(
        (h, i) => `
        <div class="hint-item">
          <span class="hint-num">${i + 1}</span>
          <span>${h}</span>
        </div>`
      )
      .join("");

    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="hot-cold-hints">${hintsHtml || "<p style='color:#aab;font-size:0.9rem'>Nenhuma dica revelada ainda.</p>"}</div>
      ${revealed < hints.length ? `<button class="secondary-btn" id="reveal-hint">Revelar dica ${revealed + 1}</button>` : ""}
      <div class="hint-text-input" style="margin-top:16px">
        <input type="text" id="hc-input" placeholder="${game.game_data.answer.split("").map(() => "_").join(" ")}" autocomplete="off">
        <button class="secondary-btn" id="hc-check">Verificar</button>
      </div>
    `;

    el.querySelector("#reveal-hint")?.addEventListener("click", () => {
      revealed++;
      draw();
    });

    el.querySelector("#hc-check").addEventListener("click", () => {
      const input = el.querySelector("#hc-input");
      const btn   = el.querySelector("#hc-check");
      const val   = input.value.trim();
      const ok    = val.toLowerCase() === answer.toLowerCase().trim();
      input.style.borderColor = ok ? "var(--green)" : "var(--coral)";
      input.style.background  = ok ? "#d4f5e2"      : "#ffe5e1";
      btn.textContent = ok ? "✓ Correto!" : "✗ Tente novamente";
      btn.style.background = ok ? "var(--green)" : "var(--coral)";
      btn.style.color = "white";
      if (ok) { input.disabled = true; btn.disabled = true; }
      setFeedback(ok ? `Correto! A resposta era "${answer}".` : "Não é essa. Tente outra vez.", ok ? "ok" : "no");
      if (ok) markComplete();
    });

    el.querySelector("#hc-input").addEventListener("keydown", (e) => {
      if (e.key === "Enter") el.querySelector("#hc-check").click();
    });
  };

  draw();
}

// ── game-rhythm-tap ───────────────────────────────────────────────────────────

function renderRhythmTap(game, el) {
  const { pattern } = game.game_data;
  let step = 0;
  let score = 0;
  let listening = false;

  function _playPatternAudio() {
    if (listening) return;
    listening = true;
    let i = 0;
    const next = () => {
      if (i >= pattern.length) { listening = false; return; }
      window.audio?.tick(pattern[i] === 1);
      i++;
      setTimeout(next, 550);
    };
    next();
  }

  const draw = () => {
    if (step >= pattern.length) { showRhythmResult(); return; }
    const isBeat = pattern[step] === 1;

    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="rhythm-pattern-display">
        ${pattern
          .map(
            (b, i) => `
          <div class="beat-box ${i < step ? "step-correct" : ""} ${i === step ? (b ? "is-beat step-active" : "is-rest step-active") : b ? "is-beat" : "is-rest"}">
            ${b ? "●" : "○"}
          </div>`
          )
          .join("")}
      </div>
      <p style="font-size:0.9rem;color:#5a6a7a;margin-bottom:4px">
        Passo ${step + 1} de ${pattern.length} — ${isBeat ? "⬤ Tempo forte!" : "○ Silêncio"}
      </p>
      <button class="secondary-btn" id="btn-listen" style="margin-bottom:12px;font-size:12px;">🔊 Ouvir padrão completo</button>
      <div class="rhythm-controls">
        <button class="tap-btn" id="btn-tap">TAP</button>
        <button class="tap-btn" id="btn-rest" style="background:var(--sky);border-color:#99a">SILÊNCIO</button>
      </div>
    `;

    el.querySelector("#btn-listen").addEventListener("click", _playPatternAudio);

    el.querySelector("#btn-tap").addEventListener("click", () => {
      window.audio?.tick(true);
      if (isBeat) score++;
      step++;
      draw();
    });
    el.querySelector("#btn-rest").addEventListener("click", () => {
      window.audio?.tick(false);
      if (!isBeat) score++;
      step++;
      draw();
    });
  };

  const showRhythmResult = () => {
    const ok = score === pattern.length;
    el.innerHTML = `
      <p class="game-prompt">Resultado</p>
      ${_resultHtml(score, pattern.length)}
      <button class="secondary-btn" id="retry-rhythm" style="margin-top:14px">Tentar novamente</button>
    `;
    setFeedback(ok ? "Perfeito! Ritmo correto." : "Pratique o padrão com calma.", ok ? "ok" : "no");
    if (ok) markComplete();
    el.querySelector("#retry-rhythm").addEventListener("click", () => {
      step = 0; score = 0; draw();
      setFeedback("", "");
    });
  };

  draw();
}

// ── game-compose ──────────────────────────────────────────────────────────────

function renderCompose(game, el) {
  const { scale, slots } = game.game_data;
  let melody = Array(slots).fill(null);
  let activeSlot = 0;

  const draw = () => {
    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="compose-slots">
        ${melody
          .map(
            (note, i) => `
          <div class="compose-slot ${note ? "filled" : ""} ${i === activeSlot && !note ? "active-slot" : ""}" data-slot="${i}">
            ${note ? `<span>${note}</span><span class="compose-note-label">${i + 1}º tempo</span>` : `<span>${i + 1}º tempo</span>`}
          </div>`
          )
          .join("")}
      </div>
      <div class="compose-scale">
        ${scale.map((note) => `<button class="note-key" data-note="${note}">${note}</button>`).join("")}
      </div>
      ${melody.some(Boolean) ? `<button class="secondary-btn" id="play-melody" style="margin-top:12px">▶ Ouvir melodia</button>` : ""}
      ${melody.every(Boolean) ? `<button class="secondary-btn" id="compose-reset" style="margin-top:8px">Recomeçar</button>` : ""}
    `;

    el.querySelectorAll(".compose-slot").forEach((slot) => {
      slot.addEventListener("click", () => {
        activeSlot = Number(slot.dataset.slot);
        draw();
      });
    });

    el.querySelectorAll(".note-key").forEach((btn) => {
      btn.addEventListener("click", () => {
        window.audio?.playNote(btn.dataset.note, 0.5);
        melody[activeSlot] = btn.dataset.note;
        if (activeSlot < slots - 1) activeSlot++;
        draw();
        if (melody.every(Boolean)) {
          setFeedback(`Melodia composta: ${melody.join(" - ")}. Criativo!`, "ok");
          markComplete();
        }
      });
    });

    el.querySelector("#play-melody")?.addEventListener("click", () => {
      const notes = melody.filter(Boolean);
      if (notes.length) window.audio?.playScale(notes, 500);
    });

    el.querySelector("#compose-reset")?.addEventListener("click", () => {
      melody = Array(slots).fill(null);
      activeSlot = 0;
      draw();
      setFeedback("", "");
    });
  };

  draw();
}

// ── game-teach ────────────────────────────────────────────────────────────────

function renderTeach(game, el) {
  const { min_chars, placeholder } = game.game_data;

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <textarea class="teach-area" id="teach-area" placeholder="${placeholder}"></textarea>
    <p class="teach-counter" id="teach-counter">0/${min_chars} caracteres</p>
    <button class="secondary-btn" id="teach-submit" disabled>Registrar explicação</button>
  `;

  const area = el.querySelector("#teach-area");
  const counter = el.querySelector("#teach-counter");
  const submit = el.querySelector("#teach-submit");

  area.addEventListener("input", () => {
    const len = area.value.trim().length;
    counter.textContent = `${len}/${min_chars} caracteres`;
    const ready = len >= min_chars;
    counter.className = `teach-counter ${ready ? "ready" : ""}`;
    submit.disabled = !ready;
  });

  submit.addEventListener("click", () => {
    setFeedback("Explicação registrada! Parabéns pelo esforço.", "ok");
    markComplete();
  });
}

// ── game-memory ───────────────────────────────────────────────────────────────

function renderMemory(game, el) {
  const { pairs } = game.game_data;
  const cards = shuffle([...pairs.flat().map((text, i) => ({ text, pairId: Math.floor(i / 2) }))]);
  let flipped = [];
  let matched = new Set();
  let locked = false;

  const draw = () => {
    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="memory-grid">
        ${cards
          .map(
            (card, i) => `
          <div class="memory-card ${flipped.includes(i) ? "flipped" : ""} ${matched.has(card.pairId) ? "matched" : ""}" data-idx="${i}">
            <div class="memory-card-inner">
              <div class="memory-front">?</div>
              <div class="memory-back">${card.text}</div>
            </div>
          </div>`
          )
          .join("")}
      </div>
    `;

    el.querySelectorAll(".memory-card").forEach((card) => {
      card.addEventListener("click", () => {
        const idx = Number(card.dataset.idx);
        if (locked || flipped.includes(idx) || matched.has(cards[idx].pairId)) return;
        if (window.audio?.isNote(cards[idx].text)) window.audio.playNote(cards[idx].text, 0.5);
        flipped.push(idx);
        draw();

        if (flipped.length === 2) {
          locked = true;
          const [a, b] = flipped;
          if (cards[a].pairId === cards[b].pairId) {
            matched.add(cards[a].pairId);
            flipped = [];
            locked = false;
            draw();
            if (matched.size === pairs.length) {
              setFeedback("Parabéns! Todos os pares encontrados.", "ok");
              markComplete();
            }
          } else {
            setTimeout(() => {
              flipped = [];
              locked = false;
              draw();
            }, 900);
          }
        }
      });
    });
  };

  draw();
}

// ── game-arrange / game-sort ──────────────────────────────────────────────────

function renderArrange(game, el) {
  const { shuffled, solution } = game.game_data;
  let order = [...shuffled];
  let selectedIdx = null;

  const draw = () => {
    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <p style="font-size:12px;color:#9CA3AF;margin-bottom:10px">Toque em dois itens para trocar de posição</p>
      <div class="arrange-list">
        ${order
          .map(
            (item, i) => `
          <div class="arrange-item${selectedIdx === i ? " arrange-selected" : ""}" data-idx="${i}" style="cursor:pointer;">
            <span style="font-size:18px;color:#aab;margin-right:4px;user-select:none;">☰</span>
            <span class="arrange-label">${item}</span>
            ${selectedIdx === i ? '<span style="font-size:11px;color:#C4943A;margin-left:auto;font-weight:700;">selecionado →</span>' : ""}
          </div>`
          )
          .join("")}
      </div>
      <button class="secondary-btn" id="check-arrange">Verificar ordem</button>
    `;

    el.querySelectorAll(".arrange-item").forEach((item) => {
      item.addEventListener("click", () => {
        const idx = Number(item.dataset.idx);
        if (selectedIdx === null) {
          selectedIdx = idx;
        } else if (selectedIdx === idx) {
          selectedIdx = null;
        } else {
          [order[selectedIdx], order[idx]] = [order[idx], order[selectedIdx]];
          selectedIdx = null;
          setFeedback("", "");
        }
        draw();
      });
    });

    el.querySelector("#check-arrange").addEventListener("click", () => {
      selectedIdx = null;
      const ok = order.every((item, i) => item === solution[i]);
      el.querySelectorAll(".arrange-item").forEach((row, i) => {
        row.classList.toggle("correct", order[i] === solution[i]);
        row.classList.toggle("wrong", order[i] !== solution[i]);
      });
      setFeedback(ok ? "Ordem correta!" : "Ainda há itens fora de lugar.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  };

  draw();
}

// ── game-quiz ─────────────────────────────────────────────────────────────────

function renderQuiz(game, el) {
  const { questions } = game.game_data;
  let idx = 0, score = 0;

  const draw = () => {
    if (idx >= questions.length) {
      const ok = score >= questions.length * 0.7;
      el.innerHTML = _resultHtml(score, questions.length);
      setFeedback(ok ? "Quiz concluído!" : "Você pode tentar novamente.", ok ? "ok" : "no");
      if (ok) markComplete();
      return;
    }

    const q = questions[idx];
    const pct = (idx / questions.length) * 100;

    el.innerHTML = `
      <div class="quiz-progress-bar-wrap"><div class="quiz-progress-bar-fill" style="width:${pct}%"></div></div>
      <p class="quiz-counter">${idx + 1} de ${questions.length}</p>
      <p class="game-prompt">${q.prompt}</p>
      <div class="choices">
        ${q.options.map((o) => `<button class="choice" data-value="${o}">${o}</button>`).join("")}
      </div>
    `;

    el.querySelectorAll(".choice").forEach((btn) => {
      btn.addEventListener("click", () => {
        el.querySelectorAll(".choice").forEach((b) => b.classList.remove("correct", "wrong"));
        const ok = btn.dataset.value === q.answer;
        btn.classList.add(ok ? "correct" : "wrong");
        if (ok) score++;
        el.querySelectorAll(".choice").forEach((b) => { b.disabled = true; });
        setTimeout(() => { idx++; draw(); }, 700);
      });
    });
  };

  draw();
}

// ── game-drag ─────────────────────────────────────────────────────────────────

function renderDragDrop(game, el) {
  const { targets, items_shuffled, solution } = game.game_data;
  const placed = {};

  const draw = () => {
    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div class="drag-board">
        <div class="drag-targets">
          ${targets
            .map(
              (label, i) => `
            <div class="drag-target" data-target-idx="${i}">
              <span class="drag-target-label">${label}</span>
              ${placed[i] !== undefined ? `<span class="drag-target-value">${placed[i]}</span>` : ""}
            </div>`
            )
            .join("")}
        </div>
        <div class="drag-items">
          ${items_shuffled
            .map((item) => {
              const isPlaced = Object.values(placed).includes(item);
              return `<div class="drag-item ${isPlaced ? "placed" : ""}" draggable="${!isPlaced}" data-item="${item}">${item}</div>`;
            })
            .join("")}
        </div>
      </div>
      <button class="secondary-btn" id="check-drag" style="margin-top:8px">Verificar</button>
    `;

    el.querySelectorAll(".drag-item:not(.placed)").forEach((item) => {
      item.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("text/plain", item.dataset.item);
        item.classList.add("dragging");
      });
      item.addEventListener("dragend", () => item.classList.remove("dragging"));
    });

    el.querySelectorAll(".drag-target").forEach((target) => {
      target.addEventListener("dragover", (e) => { e.preventDefault(); target.classList.add("drag-over"); });
      target.addEventListener("dragleave", () => target.classList.remove("drag-over"));
      target.addEventListener("drop", (e) => {
        e.preventDefault();
        target.classList.remove("drag-over");
        const item = e.dataTransfer.getData("text/plain");
        const idx = Number(target.dataset.targetIdx);
        const existing = Object.entries(placed).find(([, v]) => v === item);
        if (existing) delete placed[existing[0]];
        placed[idx] = item;
        draw();
      });
    });

    el.querySelector("#check-drag").addEventListener("click", () => {
      if (Object.keys(placed).length < targets.length) {
        setFeedback("Preencha todos os espaços antes de verificar.", "no");
        return;
      }
      const ok = targets.every((_, i) => placed[i] === solution[i]);
      el.querySelectorAll(".drag-target").forEach((t, i) => {
        t.classList.toggle("correct", placed[i] === solution[i]);
        t.classList.toggle("wrong", placed[i] !== solution[i] && placed[i] !== undefined);
      });
      setFeedback(ok ? "Perfeito! Todos no lugar certo." : "Algum item está no lugar errado.", ok ? "ok" : "no");
      if (ok) markComplete();
    });
  };

  draw();
}

// ── game-build ────────────────────────────────────────────────────────────────

function renderBuild(game, el) {
  const { time_signature, target_beats, available } = game.game_data;
  const staffId = "build-staff";
  let measure = [];

  const redrawStaff = () => {
    if (!window.VFUtils?.isReady()) return;
    if (measure.length === 0) {
      window.VFUtils.renderBlank(staffId, { timeSig: time_signature });
    } else {
      window.VFUtils.renderMeasure(staffId, measure, target_beats);
    }
  };

  const draw = () => {
    const total = measure.reduce((s, f) => s + f.beats, 0);
    const totalClass = total > target_beats ? "over" : total === target_beats ? "exact" : "";

    el.innerHTML = `
      <p class="game-prompt">${game.prompt}</p>
      <div id="${staffId}" class="vf-staff-container"></div>
      <div class="build-measure">
        <span class="build-time-sig">${time_signature}</span>
        ${measure.map((f, i) => `<span class="build-beat-chip" data-idx="${i}" title="Clique para remover">${f.name}</span>`).join("")}
        <span class="build-total ${totalClass}">${total} / ${target_beats} tempos</span>
      </div>
      <div class="build-figures">
        ${available
          .map(
            (f) => `
          <button class="build-figure-btn" data-name="${f.name}" data-beats="${f.beats}">
            <span class="build-figure-symbol">${f.symbol}</span>
            <span class="build-figure-name">${f.name}</span>
            <span class="build-figure-beats">${f.beats}t</span>
          </button>`
          )
          .join("")}
      </div>
      <button class="secondary-btn" id="check-build" style="margin-top:12px">Verificar compasso</button>
      ${measure.length ? `<button class="secondary-btn" id="reset-build" style="margin-top:8px">Limpar</button>` : ""}
    `;

    redrawStaff();

    el.querySelectorAll(".build-figure-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const f = available.find((a) => a.name === btn.dataset.name);
        if (!f) return;
        measure.push(f);
        draw();
        setFeedback("", "");
      });
    });

    el.querySelectorAll(".build-beat-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        measure.splice(Number(chip.dataset.idx), 1);
        draw();
        setFeedback("", "");
      });
    });

    el.querySelector("#check-build").addEventListener("click", () => {
      const total = measure.reduce((s, f) => s + f.beats, 0);
      const ok = total === target_beats;
      setFeedback(ok ? `Perfeito! O compasso tem exatamente ${target_beats} tempos.` : total > target_beats ? `Passou! ${total} tempos (máximo ${target_beats}).` : `Faltam ${target_beats - total} tempo(s).`, ok ? "ok" : "no");
      if (ok) markComplete();
    });

    el.querySelector("#reset-build")?.addEventListener("click", () => {
      measure = [];
      draw();
      setFeedback("", "");
    });
  };

  draw();
}

// ── game-challenge ────────────────────────────────────────────────────────────

function renderChallenge(game, el) {
  const { mission, checklist } = game.game_data;

  el.innerHTML = `
    <p class="game-prompt">${game.prompt}</p>
    <div class="challenge-mission">${mission}</div>
    <div class="challenge-checklist">
      ${checklist
        .map(
          (item, i) => `
        <label class="check-row">
          <input type="checkbox" class="challenge-check" data-idx="${i}">
          ${item}
        </label>`
        )
        .join("")}
    </div>
  `;

  const checks = el.querySelectorAll(".challenge-check");
  checks.forEach((cb) => {
    cb.addEventListener("change", () => {
      const allDone = [...checks].every((c) => c.checked);
      if (allDone) {
        setFeedback("Desafio concluído! Excelente.", "ok");
        markComplete();
      }
    });
  });
}

// ─── Start ────────────────────────────────────────────────────────────────────

// Only auto-init in the games lab context (not when loaded as a module renderer library)
const _currentScript = document.currentScript;
if (!(_currentScript && _currentScript.dataset.modulePlayer === "true")) {
  init();
}
