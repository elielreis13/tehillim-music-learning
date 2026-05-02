// ─── Dashboard do Professor ───────────────────────────────────────────────────

(async function () {

  // ── Tabs ─────────────────────────────────────────────────────────────────────

  document.querySelectorAll(".dash-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".dash-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".dash-section").forEach((s) => (s.style.display = "none"));
      tab.classList.add("active");
      document.getElementById(`tab-${tab.dataset.tab}`).style.display = "";
    });
  });

  // ── Helpers ───────────────────────────────────────────────────────────────────

  const loading = document.getElementById("dash-loading");
  const errBox  = document.getElementById("dash-error");

  function showError(msg) {
    loading.style.display = "none";
    errBox.textContent    = msg;
    errBox.style.display  = "";
  }

  async function apiFetch(path, opts = {}) {
    const r = await fetch(path, opts);
    if (!r.ok) throw new Error(`${r.status} ao buscar ${path}`);
    if (r.status === 204) return null;
    return r.json();
  }

  function fmtDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
  }

  function fmtDateTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("pt-BR", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  // ── Carregar dados iniciais ───────────────────────────────────────────────────

  let students = [], submissions = [], progress = [];
  try {
    console.log("[dashboard] carregando dados...");
    const [s, sub, p] = await Promise.all([
      apiFetch("/api/teacher/students"),
      apiFetch("/api/teacher/submissions"),
      apiFetch("/api/teacher/progress"),
    ]);
    console.log("[dashboard] dados recebidos:", { students: s, submissions: sub, progress: p });
    students    = s.students    ?? [];
    submissions = sub.submissions ?? [];
    progress    = p.progress    ?? [];
  } catch (e) {
    console.error("[dashboard] erro:", e);
    showError("Erro ao carregar dados: " + e.message);
    return;
  }

  loading.style.display = "none";

  // ── Aba Alunos ────────────────────────────────────────────────────────────────

  document.getElementById("student-count").textContent = students.length;
  const grid = document.getElementById("student-grid");

  if (!students.length) {
    grid.innerHTML = "<p class='empty-msg'>Nenhum aluno cadastrado ainda.</p>";
  } else {
    students.forEach((s) => {
      const card = document.createElement("div");
      card.className = "student-card";
      card.dataset.userId = s.id;
      const submissionCount = submissions.filter((r) => r.user_id === s.id).length;
      const displayName = s.name || s.email.split("@")[0];
      const initial = displayName[0].toUpperCase();
      card.innerHTML = `
        <div class="student-avatar">${initial}</div>
        <div class="student-info">
          <strong class="student-name">${displayName}</strong>
          <span class="student-email-sub" title="${s.email}">${s.email}</span>
          <div class="student-stats">
            <span title="Módulos com progresso">📚 ${s.modules_completed} módulos</span>
            <span title="Dias de estudo">📅 ${s.study_days} dias</span>
            <span title="Gravações enviadas">🎤 ${submissionCount} gravações</span>
          </div>
          <small class="student-last">Última atividade: ${fmtDate(s.last_activity)}</small>
        </div>
        <button class="student-open-btn" aria-label="Ver detalhes">→</button>
      `;
      card.addEventListener("click", () => openStudentDrawer(s));
      grid.appendChild(card);
    });
  }

  // ── Aba Gravações ─────────────────────────────────────────────────────────────

  document.getElementById("recordings-count").textContent = submissions.length;
  const list = document.getElementById("recordings-list");

  if (!submissions.length) {
    list.innerHTML = "<p class='empty-msg'>Nenhuma gravação enviada ainda.</p>";
  } else {
    const emailMap = Object.fromEntries(students.map((s) => [s.id, s.email]));
    submissions.forEach((sub) => renderRecordingItem(list, sub, emailMap));
  }

  function renderRecordingItem(container, sub, emailMap) {
    const item = document.createElement("div");
    item.className = "recording-item";
    const email = emailMap?.[sub.user_id] ?? sub.user_id.slice(0, 8) + "...";
    item.innerHTML = `
      <div class="recording-meta">
        <span class="recording-who">${email}</span>
        <span class="recording-module">📚 ${sub.module_slug}</span>
        <span class="recording-date">${fmtDateTime(sub.created_at)}</span>
      </div>
      ${sub.signed_url
        ? `<audio controls src="${sub.signed_url}" class="recording-audio"></audio>`
        : `<p class="rec-no-url">URL indisponível</p>`}
    `;
    container.appendChild(item);
  }

  // ── Aba Progresso ─────────────────────────────────────────────────────────────

  const wrap = document.getElementById("progress-table-wrap");

  if (!students.length || !progress.length) {
    wrap.innerHTML = "<p class='empty-msg'>Sem dados de progresso ainda.</p>";
  } else {
    const slugs = [...new Set(progress.map((p) => p.module_slug))].sort();
    const map = {};
    for (const p of progress) {
      if (!map[p.user_id]) map[p.user_id] = {};
      map[p.user_id][p.module_slug] = p.completed;
    }
    const headerCells = slugs.map((s) => `<th title="${s}">${s.replace(/-/g, " ")}</th>`).join("");
    const rows = students.map((st) => {
      const cells = slugs.map((slug) => {
        const val = map[st.id]?.[slug];
        if (!val) return `<td class="prog-none">—</td>`;
        return `<td class="prog-done" title="${val} etapas">${val}</td>`;
      }).join("");
      return `<tr><td class="prog-email">${st.email}</td>${cells}</tr>`;
    }).join("");
    wrap.innerHTML = `
      <table class="progress-table">
        <thead><tr><th>Aluno</th>${headerCells}</tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  }

  // ── Drawer de detalhe do aluno ────────────────────────────────────────────────

  const drawer     = document.getElementById("student-drawer");
  const drawerBack = document.getElementById("drawer-backdrop");

  function closeDrawer() {
    drawer.classList.remove("open");
    drawerBack.classList.remove("open");
  }

  drawerBack.addEventListener("click", closeDrawer);
  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDrawer(); });

  async function openStudentDrawer(student) {
    // Abre imediatamente com skeleton
    drawer.classList.add("open");
    drawerBack.classList.add("open");
    renderDrawerSkeleton(student);

    try {
      const data = await apiFetch(`/api/teacher/student/${student.id}`);
      renderDrawerContent(student, data);
    } catch (e) {
      document.getElementById("drawer-body").innerHTML =
        `<p class="dash-error">Erro ao carregar: ${e.message}</p>`;
    }
  }

  function renderDrawerSkeleton(student) {
    const displayName = student.name || student.email.split("@")[0];
    document.getElementById("drawer-title").textContent = displayName;
    document.getElementById("drawer-avatar").textContent = displayName[0].toUpperCase();
    document.getElementById("drawer-body").innerHTML = `<p class="skeleton-msg">Carregando...</p>`;
  }

  function renderDrawerContent(student, data) {
    const { progress, study_days, submissions: subs } = data;
    const body = document.getElementById("drawer-body");

    const totalModules = progress.length;
    const doneModules  = progress.filter((p) => p.completed > 0).length;

    // Mini calendário — últimos 30 dias
    const today    = new Date();
    const studySet = new Set(study_days);
    const calCells = Array.from({ length: 30 }, (_, i) => {
      const d = new Date(today);
      d.setDate(today.getDate() - (29 - i));
      const key = d.toISOString().split("T")[0];
      return `<span class="cal-day ${studySet.has(key) ? "active" : ""}" title="${key}"></span>`;
    }).join("");

    // Gravações por módulo (mapa slug → lista)
    const subsByMod = {};
    for (const s of subs) {
      if (!subsByMod[s.module_slug]) subsByMod[s.module_slug] = [];
      subsByMod[s.module_slug].push(s);
    }

    // Linhas de módulo — clicáveis
    const progRows = progress.length
      ? progress.map((p) => {
          const recCount = (subsByMod[p.module_slug] || []).length;
          return `
            <button class="detail-mod-row mod-clickable" data-slug="${p.module_slug}">
              <span class="detail-mod-slug">${p.module_slug.replace(/-/g, " ")}</span>
              <span class="detail-mod-steps">${p.completed} etapas</span>
              ${recCount ? `<span class="detail-mod-rec">🎤 ${recCount}</span>` : ""}
              <span class="detail-mod-date">${fmtDate(p.updated_at)}</span>
              <span class="mod-arrow">→</span>
            </button>`;
        }).join("")
      : "<p class='empty-msg'>Nenhum módulo iniciado.</p>";

    body.innerHTML = `
      <div class="detail-summary">
        <span>📚 ${doneModules}/${totalModules} módulos</span>
        <span>📅 ${study_days.length} dias de estudo</span>
        <span>🎤 ${subs.length} gravações</span>
      </div>

      <div class="detail-section">
        <h4>Dias de estudo — últimos 30 dias</h4>
        <div class="study-calendar">${calCells}</div>
      </div>

      <div class="detail-section">
        <h4>Módulos — clique para ver respostas</h4>
        <div class="detail-mod-list" id="detail-mod-list">${progRows}</div>
      </div>

      <div id="module-detail-panel" style="display:none"></div>

      <div class="detail-section" id="access-section">
        <h4>Controle de acesso</h4>
        <p class="skeleton-msg">Carregando...</p>
      </div>
    `;

    // Clique em módulo → abre painel de respostas
    body.querySelectorAll(".mod-clickable").forEach((btn) => {
      btn.addEventListener("click", () => openModulePanel(student, btn.dataset.slug, subsByMod[btn.dataset.slug] || []));
    });

    renderAccessSection(student);
  }

  async function renderAccessSection(student) {
    const section = document.getElementById("access-section");
    if (!section) return;

    let groups, slugs;
    try {
      [{ groups }, { slugs }] = await Promise.all([
        apiFetch("/api/groups"),
        apiFetch(`/api/teacher/student/${student.id}/access`),
      ]);
    } catch (e) {
      console.error("[access] erro ao carregar:", e);
      section.querySelector("p").textContent = "Erro ao carregar acesso: " + e.message;
      return;
    }

    const granted = new Set(slugs);

    const groupsHtml = groups.map((g) => {
      const allSlugs = g.modules.map((m) => m.slug);
      const allGranted = allSlugs.every((s) => granted.has(s));
      const modulesHtml = g.modules.map((m) => `
        <label class="access-mod-row">
          <input type="checkbox" class="access-check" data-slug="${m.slug}"
                 ${granted.has(m.slug) ? "checked" : ""}>
          <span class="access-mod-num">${m.number}</span>
          <span class="access-mod-title">${m.title}</span>
        </label>
      `).join("");

      return `
        <div class="access-group">
          <div class="access-group-header">
            <span class="access-group-name">${groupIconHtml(g)}${g.name}</span>
            <button class="access-group-btn ${allGranted ? "revoke" : "grant"}"
                    data-slugs="${allSlugs.join(",")}"
                    data-action="${allGranted ? "revoke" : "grant"}">
              ${allGranted ? "Revogar grupo" : "Liberar grupo"}
            </button>
          </div>
          <div class="access-mod-list">${modulesHtml}</div>
        </div>
      `;
    }).join("");

    section.innerHTML = `
      <h4>Controle de acesso</h4>
      ${groupsHtml}
      <div class="access-save-row">
        <button class="action primary" id="access-save-btn">Salvar acesso</button>
        <p class="access-save-status" id="access-save-status"></p>
      </div>
    `;

    // Botão "selecionar grupo inteiro"
    section.querySelectorAll(".access-group-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const group  = btn.closest(".access-group");
        const checks = [...group.querySelectorAll(".access-check")];
        const allOn  = checks.every((c) => c.checked);
        checks.forEach((c) => { c.checked = !allOn; });
        refreshGroupBtn(group);
      });
    });

    // Atualiza botão de grupo ao mudar qualquer checkbox
    section.querySelectorAll(".access-check").forEach((cb) => {
      cb.addEventListener("change", () => refreshGroupBtn(cb.closest(".access-group")));
    });

    // Salvar tudo de uma vez
    document.getElementById("access-save-btn").addEventListener("click", async () => {
      const btn      = document.getElementById("access-save-btn");
      const statusEl = document.getElementById("access-save-status");
      const slugs    = [...section.querySelectorAll(".access-check:checked")].map((c) => c.dataset.slug);

      btn.disabled     = true;
      btn.textContent  = "Salvando...";
      statusEl.textContent = "";
      statusEl.className   = "access-save-status";

      try {
        await apiFetch(`/api/teacher/student/${student.id}/access`, {
          method:  "PUT",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ slugs }),
        });
        statusEl.textContent = `✓ Acesso salvo — ${slugs.length} módulo(s) liberado(s)`;
        statusEl.className   = "access-save-status ok";
      } catch (e) {
        statusEl.textContent = "Erro ao salvar: " + e.message;
        statusEl.className   = "access-save-status error";
      } finally {
        btn.disabled    = false;
        btn.textContent = "Salvar acesso";
      }
    });
  }

  function groupIconHtml(group) {
    return group && group.icon_file
      ? `<img src="/static/icons/${group.icon_file}" alt="" class="access-group-icon">`
      : `${group ? group.icon : ""} `;
  }

  function refreshGroupBtn(group) {
    const checks    = [...group.querySelectorAll(".access-check")];
    const allGranted = checks.every((c) => c.checked);
    const btn = group.querySelector(".access-group-btn");
    btn.textContent = allGranted ? "Desmarcar grupo" : "Selecionar grupo";
    btn.className   = `access-group-btn ${allGranted ? "revoke" : "grant"}`;
  }

  // ── Painel de módulo (respostas + gravações + comentário) ─────────────────────

  async function openModulePanel(student, moduleSlug, modSubs) {
    const panel = document.getElementById("module-detail-panel");
    panel.style.display = "";
    panel.innerHTML = `<p class="skeleton-msg">Carregando respostas...</p>`;
    panel.scrollIntoView({ behavior: "smooth", block: "start" });

    let answers = [], comments = [];
    try {
      ({ answers, comments } = await apiFetch(`/api/teacher/student/${student.id}/module/${moduleSlug}`));
    } catch (e) {
      panel.innerHTML = `<p class="dash-error">Erro: ${e.message}</p>`;
      return;
    }

    // Respostas agrupadas por step_index
    const byStep = {};
    for (const a of answers) {
      if (!byStep[a.step_index]) byStep[a.step_index] = [];
      byStep[a.step_index].push(a);
    }

    const answersHtml = Object.keys(byStep).length
      ? Object.entries(byStep).map(([idx, attempts]) => {
          const last    = attempts[attempts.length - 1];
          const tries   = attempts.length;
          const correct = last.correct;
          const attemptsHtml = attempts.map((a) =>
            `<span class="attempt-chip ${a.correct ? "ok" : "no"}">${a.answer}</span>`
          ).join("");
          return `
            <div class="answer-row ${correct ? "answer-correct" : "answer-wrong"}">
              <div class="answer-question">${last.question || `Etapa ${Number(idx) + 1}`}</div>
              <div class="answer-attempts">${attemptsHtml}</div>
              <div class="answer-meta">
                ${correct ? "✓ Acertou" : "✗ Não acertou"}
                ${tries > 1 ? `· ${tries} tentativas` : ""}
                <span class="answer-date">${fmtDateTime(last.created_at)}</span>
              </div>
            </div>`;
        }).join("")
      : "<p class='empty-msg'>Nenhuma resposta registrada para este módulo.</p>";

    // Gravações do módulo
    const subsHtml = modSubs.length
      ? modSubs.map((s) => `
          <div class="detail-sub-item">
            <div class="detail-sub-meta">
              <span class="recording-date">${fmtDateTime(s.created_at)}</span>
            </div>
            ${s.signed_url
              ? `<audio controls src="${s.signed_url}" class="recording-audio"></audio>`
              : `<p class="rec-no-url">URL indisponível</p>`}
          </div>`).join("")
      : "";

    // Comentários existentes para este módulo
    const commentsHtml = comments.length
      ? comments.map((c) => `
          <div class="comment-item" data-id="${c.id}">
            <div class="comment-header">
              <span class="comment-date">${fmtDateTime(c.created_at)}</span>
              <button class="comment-delete" data-id="${c.id}" title="Excluir">✕</button>
            </div>
            <p class="comment-content">${c.content}</p>
          </div>`).join("")
      : "<p class='empty-msg' id='no-comments-msg'>Nenhum comentário ainda.</p>";

    panel.innerHTML = `
      <div class="module-panel-header">
        <button class="mod-back-btn" id="mod-back-btn">← Voltar</button>
        <h3 class="module-panel-title">${moduleSlug.replace(/-/g, " ")}</h3>
      </div>

      <div class="detail-section">
        <h4>Respostas do aluno</h4>
        ${answersHtml}
      </div>

      ${modSubs.length ? `<div class="detail-section"><h4>Gravações</h4>${subsHtml}</div>` : ""}

      <div class="detail-section">
        <h4>Comentários sobre este módulo</h4>
        <div class="comments-list" id="comments-list">${commentsHtml}</div>
        <form class="comment-form" id="comment-form">
          <textarea
            id="comment-text"
            class="comment-textarea"
            placeholder="Escreva um feedback sobre este módulo..."
            rows="3"
            required
          ></textarea>
          <button type="submit" class="action primary comment-submit">Enviar comentário</button>
          <p class="comment-status" id="comment-status" aria-live="polite"></p>
        </form>
      </div>
    `;

    document.getElementById("mod-back-btn").addEventListener("click", () => {
      panel.style.display = "none";
      document.getElementById("detail-mod-list").scrollIntoView({ behavior: "smooth" });
    });

    document.getElementById("comment-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const content  = document.getElementById("comment-text").value.trim();
      const statusEl = document.getElementById("comment-status");
      const btn      = e.target.querySelector(".comment-submit");
      if (!content) return;

      btn.disabled = true;
      statusEl.textContent = "Enviando...";
      statusEl.className   = "comment-status";

      try {
        const newComment = await apiFetch("/api/teacher/comments", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ student_id: student.id, content, module_slug: moduleSlug }),
        });

        statusEl.textContent = "✓ Enviado!";
        statusEl.className   = "comment-status ok";
        document.getElementById("comment-text").value = "";

        const list  = document.getElementById("comments-list");
        const noMsg = document.getElementById("no-comments-msg");
        if (noMsg) noMsg.remove();

        const div = document.createElement("div");
        div.className  = "comment-item";
        div.dataset.id = newComment.id;
        div.innerHTML  = `
          <div class="comment-header">
            <span class="comment-date">${fmtDateTime(newComment.created_at)}</span>
            <button class="comment-delete" data-id="${newComment.id}" title="Excluir">✕</button>
          </div>
          <p class="comment-content">${newComment.content}</p>
        `;
        list.insertAdjacentElement("afterbegin", div);
        attachDeleteHandlers(panel);
      } catch (err) {
        statusEl.textContent = "Erro: " + err.message;
        statusEl.className   = "comment-status error";
      } finally {
        btn.disabled = false;
      }
    });

    attachDeleteHandlers(panel);
  }

  function attachDeleteHandlers(scope = document) {
    scope.querySelectorAll(".comment-delete").forEach((btn) => {
      btn.replaceWith(btn.cloneNode(true));
    });
    scope.querySelectorAll(".comment-delete").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!confirm("Excluir este comentário?")) return;
        try {
          await apiFetch(`/api/teacher/comments/${btn.dataset.id}`, { method: "DELETE" });
          btn.closest(".comment-item").remove();
        } catch (e) {
          alert("Erro ao excluir: " + e.message);
        }
      });
    });
  }

})();
