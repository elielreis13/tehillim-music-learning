// ─── Admin — Gerenciamento de Alunos ─────────────────────────────────────────

(async function () {

  // Aguarda auth antes de qualquer chamada
  if (window.auth) await window.auth.ready;

  // ── Helpers ───────────────────────────────────────────────────────────────────

  async function api(path, { headers: extraHeaders = {}, ...restOpts } = {}) {
    const token = window.auth?.session?.access_token;
    const headers = {
      "Content-Type": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
      ...extraHeaders,
    };
    const r = await fetch(path, { headers, ...restOpts });
    if (r.status === 204) return null;
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
  }

  function setFeedback(id, msg, type = "") {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    const colorMap = { ok: "#4E7A60", error: "#ef4444", "": "#6b7280" };
    el.style.color = colorMap[type] ?? colorMap[""];
  }

  // ── Toggle mostrar senha ──────────────────────────────────────────────────────

  document.querySelectorAll(".toggle-pw").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = document.getElementById(btn.dataset.target);
      input.type = input.type === "password" ? "text" : "password";
    });
  });

  // ── Abrir / fechar formulário de criação ──────────────────────────────────────

  const createCard = document.getElementById("create-form-card");

  function openCreateCard() {
    if (!createCard) return;
    createCard.style.display = "";
    document.getElementById("new-email")?.focus();
  }
  function closeCreateCard() {
    if (!createCard) return;
    createCard.style.display = "none";
    document.getElementById("create-form")?.reset();
    setFeedback("create-feedback", "");
  }

  document.getElementById("open-create-btn")?.addEventListener("click", openCreateCard);
  document.getElementById("cancel-create-btn")?.addEventListener("click", closeCreateCard);

  // Expõe para chamada do template (botão no header)
  window.openCreateModal  = openCreateCard;
  window.closeCreateModal = closeCreateCard;

  // ── Criar aluno ───────────────────────────────────────────────────────────────

  document.getElementById("create-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name     = document.getElementById("new-name").value.trim();
    const email    = document.getElementById("new-email").value.trim();
    const password = document.getElementById("new-password").value;
    const btn      = document.getElementById("create-btn");

    btn.disabled = true;
    btn.textContent = "Criando...";
    setFeedback("create-feedback", "");

    try {
      await api("/api/admin/create-user", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
      setFeedback("create-feedback", `✓ Aluno ${email} criado com sucesso!`, "ok");
      document.getElementById("create-form").reset();
      await loadStudents();
    } catch (err) {
      setFeedback("create-feedback", "Erro: " + err.message, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "Criar Aluno";
    }
  });

  // ── Carregar lista de alunos ──────────────────────────────────────────────────

  const loading  = document.getElementById("admin-loading");
  const errBox   = document.getElementById("admin-error");
  const listEl   = document.getElementById("admin-student-list");
  const noResult = document.getElementById("admin-no-results");

  let _allStudents = [];
  let _currentSort = "name";
  let _currentQuery = "";
  let _currentTeacher = null; // teacher_id filter (null = todos)

  async function loadStudents() {
    if (loading) loading.style.display = "";
    if (listEl)  listEl.innerHTML = "";

    try {
      const { students } = await api("/api/teacher/students");
      if (loading) loading.style.display = "none";
      _allStudents = students;
      renderStats(students);
      renderTeacherStrip();
      applyFilterSort();
    } catch (err) {
      if (loading) loading.style.display = "none";
      if (errBox) {
        errBox.textContent   = "Erro ao carregar: " + err.message;
        errBox.style.display = "";
      }
    }
  }

  function applyFilterSort() {
    let list = [..._allStudents];

    // Filtro por professor
    if (_currentTeacher) {
      list = list.filter(s => s.teacher_id === _currentTeacher);
    }

    // Filtro por busca
    const q = _currentQuery.toLowerCase().trim();
    if (q) {
      list = list.filter(s => {
        const name = (s.name || "").toLowerCase();
        const email = (s.email || "").toLowerCase();
        return name.includes(q) || email.includes(q);
      });
    }

    if (_currentSort === "name") {
      list.sort((a, b) => (a.name || a.email).localeCompare(b.name || b.email, "pt-BR"));
    } else if (_currentSort === "activity") {
      list.sort((a, b) => (b.last_activity || "").localeCompare(a.last_activity || ""));
    } else if (_currentSort === "progress") {
      list.sort((a, b) => (b.modules_completed - a.modules_completed) || (b.study_days - a.study_days));
    }
    renderStudents(list);
  }

  function renderTeacherStrip() {
    const strip = document.getElementById("teacher-strip");
    const chips = document.getElementById("teacher-chips");
    if (!strip || !chips) return;

    // Apenas professores (role teacher, não owner)
    const teachers = _allStudents.filter(u => u.role === "teacher");
    if (!teachers.length) { strip.style.display = "none"; return; }

    // Conta alunos por professor
    const countMap = {};
    _allStudents.forEach(s => {
      if (s.teacher_id) countMap[s.teacher_id] = (countMap[s.teacher_id] || 0) + 1;
    });

    strip.style.display = "";

    function chip(label, count, id) {
      const el = document.createElement("button");
      const isActive = id === _currentTeacher;
      el.style.cssText = `
        display:inline-flex;align-items:center;gap:5px;
        font-size:12px;font-weight:600;padding:5px 12px;border-radius:999px;
        border:1.5px solid ${isActive ? "#C4943A" : "#E5E7EB"};
        background:${isActive ? "#C4943A" : "white"};
        color:${isActive ? "white" : "#374151"};
        cursor:pointer;white-space:nowrap;transition:all .15s;flex-shrink:0;
      `;
      el.innerHTML = label + (count != null ? ` <span style="background:${isActive ? "rgba(255,255,255,.3)" : "#F3F4F6"};padding:1px 6px;border-radius:999px;font-size:10px;">${count}</span>` : "");
      el.addEventListener("click", () => {
        _currentTeacher = id;
        renderTeacherStrip();
        applyFilterSort();
      });
      return el;
    }

    chips.innerHTML = "";
    chips.appendChild(chip("Todos", _allStudents.filter(s => s.role !== "teacher" && s.role !== "owner").length, null));
    teachers.sort((a, b) => (a.name || a.email).localeCompare(b.name || b.email, "pt-BR"));
    teachers.forEach(t => {
      chips.appendChild(chip(t.name || t.email.split("@")[0], countMap[t.id] || 0, t.id));
    });
  }

  window._adminFilterStudents = function(query) {
    _currentQuery = query;
    applyFilterSort();
  };

  window._adminSortStudents = function(sortKey) {
    _currentSort = sortKey;
    applyFilterSort();
  };

  function renderStats(students) {
    const totalEl     = document.getElementById("stat-total");
    const completedEl = document.getElementById("stat-completed");
    const daysEl      = document.getElementById("stat-days");
    const activeEl    = document.getElementById("stat-active");

    if (!totalEl) return;
    const students_ = students.filter(s => s.role !== "teacher");
    totalEl.textContent     = students_.length;
    completedEl.textContent = students_.reduce((s, u) => s + u.modules_completed, 0);
    daysEl.textContent      = students_.reduce((s, u) => s + u.study_days, 0);

    const oneWeekAgo = new Date(Date.now() - 7 * 86400000).toISOString();
    activeEl.textContent = students_.filter(u => u.last_activity && u.last_activity > oneWeekAgo).length;
  }

  function renderStudents(students) {
    if (!listEl) return;
    listEl.innerHTML = "";

    if (!students.length) {
      if (noResult) noResult.style.display = "";
      return;
    }
    if (noResult) noResult.style.display = "none";

    // Mapa id → nome para exibir o professor dono do aluno
    const teacherMap = {};
    _allStudents.forEach(u => {
      if (u.role === "teacher" || u.role === "owner") {
        teacherMap[u.id] = u.name || u.email.split("@")[0];
      }
    });

    students.forEach((s) => {
      const displayName = s.name || s.email.split("@")[0];
      const isOwner     = s.role === "owner";
      const isTeacher   = s.role === "teacher" || isOwner;
      const initial     = displayName[0].toUpperCase();
      const avatarBg    = isOwner ? "#FDE8D0" : isTeacher ? "#E8E0F4" : "#EDD9B0";
      const avatarColor = isOwner ? "#C4520A" : isTeacher ? "#7B5EA7" : "#C4943A";

      const lastActivity = s.last_activity
        ? new Date(s.last_activity).toLocaleDateString("pt-BR", { day: "numeric", month: "short" })
        : "—";

      const progressPct = Math.min(100, s.modules_completed * 5);

      const card = document.createElement("div");
      card.className = "s-card" + (isOwner ? " is-teacher" : isTeacher ? " is-teacher" : "");
      if (!isOwner && !isTeacher) {
        card.style.cursor = "pointer";
        card.addEventListener("click", e => {
          if (e.target.closest("button")) return;
          window.location.href = `/professor/alunos/${s.id}`;
        });
      }

      card.innerHTML = `
        <div style="display:flex;align-items:center;gap:10px;">
          <div style="width:42px;height:42px;border-radius:50%;background:${avatarBg};color:${avatarColor};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;flex-shrink:0;">${initial}</div>
          <div style="min-width:0;flex:1;">
            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;">
              <span style="font-weight:700;font-size:13px;color:#1f2937;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:120px;">${displayName}</span>
              ${isOwner   ? '<span style="font-size:9px;background:#FDE8D0;color:#C4520A;padding:2px 7px;border-radius:999px;font-weight:700;flex-shrink:0;">Owner</span>' : ""}
              ${!isOwner && isTeacher ? '<span style="font-size:9px;background:#E8E0F4;color:#7B5EA7;padding:2px 7px;border-radius:999px;font-weight:700;flex-shrink:0;">Prof.</span>' : ""}
            </div>
            <p style="font-size:11px;color:#9C8460;margin:2px 0 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${s.email}</p>
            ${s.teacher_id && teacherMap[s.teacher_id] ? `<p style="font-size:10px;color:#C4943A;margin:2px 0 0;display:flex;align-items:center;gap:3px;"><svg width="10" height="10" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>${teacherMap[s.teacher_id]}</p>` : ""}
          </div>
        </div>

        <div style="display:flex;gap:12px;">
          <div style="text-align:center;flex:1;">
            <p style="font-size:16px;font-weight:700;color:#C4943A;margin:0;">${s.modules_completed}</p>
            <p style="font-size:9px;color:#9C8460;text-transform:uppercase;letter-spacing:.08em;margin:1px 0 0;">Módulos</p>
          </div>
          <div style="text-align:center;flex:1;">
            <p style="font-size:16px;font-weight:700;color:#4E7A60;margin:0;">${s.study_days}</p>
            <p style="font-size:9px;color:#9C8460;text-transform:uppercase;letter-spacing:.08em;margin:1px 0 0;">Dias</p>
          </div>
          <div style="text-align:center;flex:1;">
            <p style="font-size:12px;font-weight:600;color:#374151;margin:0;">${lastActivity}</p>
            <p style="font-size:9px;color:#9C8460;text-transform:uppercase;letter-spacing:.08em;margin:1px 0 0;">Ativo</p>
          </div>
        </div>

        <div style="height:4px;background:#F0E8D4;border-radius:2px;overflow:hidden;">
          <div style="height:100%;width:${progressPct}%;background:#C4943A;border-radius:2px;transition:width .6s;"></div>
        </div>

        <div style="display:flex;gap:5px;flex-wrap:wrap;border-top:1px solid #F0E8D4;padding-top:10px;">
          ${isOwner ? `
          <span style="font-size:11px;color:#9C8460;font-style:italic;padding:4px 2px;">Conta protegida</span>
          ` : `
          <button class="s-action reset-btn" data-id="${s.id}" data-email="${s.email}"
                  style="background:#F3F4F6;color:#374151;">Senha</button>
          ${!isTeacher ? `
          <button class="s-action access-btn" data-id="${s.id}" data-name="${displayName}"
                  style="background:#FBF6EE;color:#C4943A;flex:1;">Acesso</button>
          <button class="s-action teacher-btn" data-id="${s.id}"
                  style="background:#F3F4F6;color:#374151;">Prof.</button>` : ""}
          <button class="s-action delete-btn" data-id="${s.id}" data-email="${s.email}"
                  style="background:#FEF2F2;color:#ef4444;">✕</button>
          `}
        </div>
      `;
      listEl.appendChild(card);
    });

    listEl.querySelectorAll(".reset-btn").forEach((btn) => {
      btn.addEventListener("click", () => openResetModal(btn.dataset.id, btn.dataset.email));
    });
    listEl.querySelectorAll(".teacher-btn").forEach((btn) => {
      btn.addEventListener("click", () => setTeacher(btn.dataset.id));
    });
    listEl.querySelectorAll(".access-btn").forEach((btn) => {
      btn.addEventListener("click", () => openAccessModal(btn.dataset.id, btn.dataset.name));
    });
    listEl.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => deleteStudent(btn.dataset.id, btn.dataset.email));
    });
  }

  // ── Modal reset de senha ──────────────────────────────────────────────────────

  let resetUserId = null;

  function openResetModal(userId, email) {
    resetUserId = userId;
    const label = document.getElementById("reset-email-label");
    if (label) label.textContent = email;
    document.getElementById("reset-form")?.reset();
    setFeedback("reset-feedback", "");
    const backdrop = document.getElementById("reset-backdrop");
    if (backdrop) backdrop.style.display = "";
    document.getElementById("reset-password")?.focus();
  }

  function closeResetModal() {
    const backdrop = document.getElementById("reset-backdrop");
    if (backdrop) backdrop.style.display = "none";
    resetUserId = null;
  }

  document.getElementById("cancel-reset-btn")?.addEventListener("click", closeResetModal);
  document.getElementById("reset-backdrop")?.addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeResetModal();
  });

  document.getElementById("reset-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const password = document.getElementById("reset-password").value;
    const btn      = document.getElementById("reset-btn");

    btn.disabled = true;
    btn.textContent = "Salvando...";
    setFeedback("reset-feedback", "");

    try {
      await api("/api/admin/reset-password", {
        method: "POST",
        body: JSON.stringify({ user_id: resetUserId, password }),
      });
      setFeedback("reset-feedback", "✓ Senha redefinida com sucesso!", "ok");
      setTimeout(closeResetModal, 1200);
    } catch (err) {
      setFeedback("reset-feedback", "Erro: " + err.message, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "Salvar Senha";
    }
  });

  // ── Marcar como professor ─────────────────────────────────────────────────────

  async function setTeacher(userId) {
    if (!confirm("Marcar esta conta como professor?\n\nEla ficará isenta do controle de acesso.")) return;
    try {
      await api(`/api/admin/set-teacher/${userId}`, { method: "POST" });
      await loadStudents();
    } catch (err) {
      alert("Erro: " + err.message);
    }
  }

  // ── Excluir aluno ─────────────────────────────────────────────────────────────

  async function deleteStudent(userId, email) {
    if (!confirm(`Excluir o aluno "${email}"?\n\nEsta ação é irreversível e apaga todo o progresso.`)) return;
    try {
      await api(`/api/admin/delete-user/${userId}`, { method: "DELETE" });
      await loadStudents();
    } catch (err) {
      alert("Erro ao excluir: " + err.message);
    }
  }

  // ── Modal de acesso ───────────────────────────────────────────────────────────

  let accessUserId = null;

  async function openAccessModal(userId, name) {
    accessUserId = userId;
    const label = document.getElementById("access-modal-label");
    const body  = document.getElementById("access-modal-body");
    if (label) label.textContent = name;
    if (body)  body.innerHTML = '<p style="padding:16px;font-size:13px;color:#9ca3af">Carregando módulos...</p>';
    const backdrop = document.getElementById("access-backdrop");
    if (backdrop) backdrop.style.display = "";

    let groups, slugs;
    try {
      [{ groups }, { slugs }] = await Promise.all([
        api("/api/groups"),
        api(`/api/teacher/student/${userId}/access`),
      ]);
    } catch (err) {
      if (body) body.innerHTML = `<p style="padding:16px;font-size:13px;color:#ef4444">Erro: ${err.message}</p>`;
      return;
    }

    const granted = new Set(slugs);

    const groupsHtml = groups.map((g) => {
      const allSlugs   = g.modules.map((m) => m.slug);
      const allGranted = allSlugs.length > 0 && allSlugs.every((s) => granted.has(s));
      const modulesHtml = g.modules.map((m) => `
        <label style="display:flex;align-items:center;gap:10px;padding:8px 12px;border-radius:10px;cursor:pointer;margin-bottom:2px" onmouseover="this.style.background='#f9fafb'" onmouseout="this.style.background=''">
          <input type="checkbox" class="access-check" data-slug="${m.slug}" ${granted.has(m.slug) ? "checked" : ""}
                 style="width:16px;height:16px;accent-color:#C4943A;cursor:pointer">
          <span style="font-size:11px;font-weight:700;color:#C4943A;background:#FBF6EE;padding:2px 6px;border-radius:5px;flex-shrink:0">M${String(m.number).padStart(2, "0")}</span>
          <span style="font-size:13px;color:#374151">${m.title}</span>
        </label>
      `).join("");

      const btnStyle = allGranted
        ? "font-size:11px;font-weight:600;padding:4px 10px;border-radius:7px;background:#fef2f2;color:#ef4444;border:none;cursor:pointer"
        : "font-size:11px;font-weight:600;padding:4px 10px;border-radius:7px;background:#FBF6EE;color:#C4943A;border:none;cursor:pointer";

      return `
        <div class="access-group" style="margin-bottom:12px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;padding:0 4px">
            <div style="display:flex;align-items:center;gap:8px">
              <img src="/static/icons/${g.icon_file}" style="width:18px;height:18px;object-fit:contain">
              <span style="font-weight:600;font-size:13px;color:#1f2937">${g.name}</span>
            </div>
            <button class="access-group-btn" data-action="${allGranted ? "revoke" : "grant"}" style="${btnStyle}">
              ${allGranted ? "Revogar grupo" : "Liberar grupo"}
            </button>
          </div>
          <div>${modulesHtml}</div>
        </div>
      `;
    }).join("");

    if (body) body.innerHTML = `
      ${groupsHtml}
      <div style="border-top:1px solid #f3f4f6;padding-top:16px;margin-top:4px;display:flex;align-items:center;gap:12px">
        <button id="access-save-btn"
                style="flex:1;background:#C4943A;color:#fff;font-weight:600;font-size:13px;padding:10px;border-radius:12px;border:none;cursor:pointer">
          Salvar acesso
        </button>
        <p id="access-save-status" style="font-size:12px;color:#6b7280"></p>
      </div>
    `;

    body.querySelectorAll(".access-group-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const group  = btn.closest(".access-group");
        const checks = [...group.querySelectorAll(".access-check")];
        const allOn  = checks.every((c) => c.checked);
        checks.forEach((c) => { c.checked = !allOn; });
        const nowAllOn = checks.every((c) => c.checked);
        const isRevoke = nowAllOn;
        btn.style.cssText = isRevoke
          ? "font-size:11px;font-weight:600;padding:4px 10px;border-radius:7px;background:#fef2f2;color:#ef4444;border:none;cursor:pointer"
          : "font-size:11px;font-weight:600;padding:4px 10px;border-radius:7px;background:#FBF6EE;color:#C4943A;border:none;cursor:pointer";
        btn.textContent = isRevoke ? "Revogar grupo" : "Liberar grupo";
        btn.dataset.action = isRevoke ? "revoke" : "grant";
      });
    });

    document.getElementById("access-save-btn")?.addEventListener("click", async () => {
      const saveBtn  = document.getElementById("access-save-btn");
      const statusEl = document.getElementById("access-save-status");
      const selected = [...body.querySelectorAll(".access-check:checked")].map((c) => c.dataset.slug);

      saveBtn.disabled     = true;
      saveBtn.textContent  = "Salvando...";
      statusEl.textContent = "";

      try {
        await api(`/api/teacher/student/${accessUserId}/access`, {
          method: "PUT",
          body:   JSON.stringify({ slugs: selected }),
        });
        statusEl.textContent = `✓ ${selected.length} módulo(s) liberado(s)`;
        statusEl.style.color = "#4E7A60";
      } catch (err) {
        statusEl.textContent = "Erro ao salvar: " + err.message;
        statusEl.style.color = "#ef4444";
      } finally {
        saveBtn.disabled    = false;
        saveBtn.textContent = "Salvar acesso";
      }
    });
  }

  function closeAccessModal() {
    const backdrop = document.getElementById("access-backdrop");
    if (backdrop) backdrop.style.display = "none";
    accessUserId = null;
  }

  document.getElementById("cancel-access-btn")?.addEventListener("click", closeAccessModal);
  document.getElementById("access-backdrop")?.addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeAccessModal();
  });

  // ── Init ──────────────────────────────────────────────────────────────────────

  await loadStudents();

})();
