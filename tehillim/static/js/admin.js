// ─── Admin — Gerenciamento de Alunos ─────────────────────────────────────────

(async function () {

  // ── Helpers ───────────────────────────────────────────────────────────────────

  async function api(path, opts = {}) {
    const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    if (r.status === 204) return null;
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
  }

  function setFeedback(id, msg, type = "") {
    const el = document.getElementById(id);
    el.textContent = msg;
    el.className   = `admin-feedback ${type}`;
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
  document.getElementById("open-create-btn").addEventListener("click", () => {
    createCard.style.display = "";
    document.getElementById("new-email").focus();
  });
  document.getElementById("cancel-create-btn").addEventListener("click", () => {
    createCard.style.display = "none";
    document.getElementById("create-form").reset();
    setFeedback("create-feedback", "");
  });

  // ── Criar aluno ───────────────────────────────────────────────────────────────

  document.getElementById("create-form").addEventListener("submit", async (e) => {
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
      btn.textContent = "Criar aluno";
    }
  });

  // ── Carregar lista de alunos ──────────────────────────────────────────────────

  const loading   = document.getElementById("admin-loading");
  const errBox    = document.getElementById("admin-error");
  const listEl    = document.getElementById("admin-student-list");

  async function loadStudents() {
    loading.style.display = "";
    listEl.innerHTML      = "";

    try {
      const { students } = await api("/api/teacher/students");
      loading.style.display = "none";
      renderStudents(students);
    } catch (err) {
      loading.style.display = "none";
      errBox.textContent    = "Erro ao carregar: " + err.message;
      errBox.style.display  = "";
    }
  }

  function renderStudents(students) {
    if (!students.length) {
      listEl.innerHTML = "<p class='empty-msg'>Nenhum aluno cadastrado ainda.</p>";
      return;
    }

    students.forEach((s) => {
      const row = document.createElement("div");
      row.className = "admin-student-row";
      const displayName = s.name || s.email.split("@")[0];
      const isTeacher   = s.role === "teacher";
      row.innerHTML = `
        <div class="admin-student-avatar">${displayName[0].toUpperCase()}</div>
        <div class="admin-student-info">
          <strong>${displayName}</strong>
          <span class="admin-student-email">${s.email}</span>
          <span class="admin-student-meta">
            📚 ${s.modules_completed} módulos &nbsp;·&nbsp;
            📅 ${s.study_days} dias &nbsp;·&nbsp;
            Última atividade: ${s.last_activity ? new Date(s.last_activity).toLocaleDateString("pt-BR") : "—"}
          </span>
        </div>
        <div class="admin-student-actions">
          <button class="admin-btn reset-btn" data-id="${s.id}" data-email="${s.email}">
            🔑 Redefinir senha
          </button>
          ${isTeacher ? `<span class="teacher-badge">👨‍🏫 Professor</span>` : `
          <button class="admin-btn teacher-btn" data-id="${s.id}" title="Marcar como professor">
            👨‍🏫
          </button>`}
          ${!isTeacher ? `
          <button class="admin-btn access-btn" data-id="${s.id}" data-name="${displayName}">
            🔓 Acesso
          </button>` : ""}
          <button class="admin-btn delete-btn danger" data-id="${s.id}" data-email="${s.email}">
            🗑 Excluir
          </button>
        </div>
      `;
      listEl.appendChild(row);
    });

    // Reset senha
    listEl.querySelectorAll(".reset-btn").forEach((btn) => {
      btn.addEventListener("click", () => openResetModal(btn.dataset.id, btn.dataset.email));
    });

    // Marcar como professor
    listEl.querySelectorAll(".teacher-btn").forEach((btn) => {
      btn.addEventListener("click", () => setTeacher(btn.dataset.id));
    });

    // Controle de acesso
    listEl.querySelectorAll(".access-btn").forEach((btn) => {
      btn.addEventListener("click", () => openAccessModal(btn.dataset.id, btn.dataset.name));
    });

    // Excluir
    listEl.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => deleteStudent(btn.dataset.id, btn.dataset.email));
    });
  }

  // ── Modal reset de senha ──────────────────────────────────────────────────────

  let resetUserId = null;

  function openResetModal(userId, email) {
    resetUserId = userId;
    document.getElementById("reset-email-label").textContent = email;
    document.getElementById("reset-form").reset();
    setFeedback("reset-feedback", "");
    document.getElementById("reset-backdrop").style.display = "";
    document.getElementById("reset-password").focus();
  }

  function closeResetModal() {
    document.getElementById("reset-backdrop").style.display = "none";
    resetUserId = null;
  }

  document.getElementById("cancel-reset-btn").addEventListener("click", closeResetModal);
  document.getElementById("reset-backdrop").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeResetModal();
  });

  document.getElementById("reset-form").addEventListener("submit", async (e) => {
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
      btn.textContent = "Salvar nova senha";
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
    document.getElementById("access-modal-label").textContent = name;
    document.getElementById("access-modal-body").innerHTML = "<p class='dash-loading'>Carregando módulos...</p>";
    document.getElementById("access-backdrop").style.display = "";

    let groups, slugs;
    try {
      [{ groups }, { slugs }] = await Promise.all([
        api("/api/groups"),
        api(`/api/teacher/student/${userId}/access`),
      ]);
    } catch (err) {
      document.getElementById("access-modal-body").innerHTML = `<p class='dash-error'>Erro: ${err.message}</p>`;
      return;
    }

    const granted = new Set(slugs);

    const groupsHtml = groups.map((g) => {
      const allSlugs   = g.modules.map((m) => m.slug);
      const allGranted = allSlugs.every((s) => granted.has(s));
      const modulesHtml = g.modules.map((m) => `
        <label class="access-mod-row">
          <input type="checkbox" class="access-check" data-slug="${m.slug}" ${granted.has(m.slug) ? "checked" : ""}>
          <span class="access-mod-num">${m.number}</span>
          <span class="access-mod-title">${m.title}</span>
        </label>
      `).join("");
      return `
        <div class="access-group">
          <div class="access-group-header">
            <span class="access-group-name">${groupIconHtml(g)}${g.name}</span>
            <button class="access-group-btn ${allGranted ? "revoke" : "grant"}"
                    data-action="${allGranted ? "revoke" : "grant"}">
              ${allGranted ? "Revogar grupo" : "Liberar grupo"}
            </button>
          </div>
          <div class="access-mod-list">${modulesHtml}</div>
        </div>
      `;
    }).join("");

    document.getElementById("access-modal-body").innerHTML = `
      ${groupsHtml}
      <div class="access-save-row">
        <button class="action primary" id="access-save-btn">Salvar acesso</button>
        <p class="access-save-status" id="access-save-status"></p>
      </div>
    `;

    const body = document.getElementById("access-modal-body");

    body.querySelectorAll(".access-group-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const group  = btn.closest(".access-group");
        const checks = [...group.querySelectorAll(".access-check")];
        const allOn  = checks.every((c) => c.checked);
        checks.forEach((c) => { c.checked = !allOn; });
        const nowAllOn = checks.every((c) => c.checked);
        btn.className   = `access-group-btn ${nowAllOn ? "revoke" : "grant"}`;
        btn.textContent = nowAllOn ? "Revogar grupo" : "Liberar grupo";
      });
    });

    document.getElementById("access-save-btn").addEventListener("click", async () => {
      const saveBtn  = document.getElementById("access-save-btn");
      const statusEl = document.getElementById("access-save-status");
      const selected = [...body.querySelectorAll(".access-check:checked")].map((c) => c.dataset.slug);

      saveBtn.disabled    = true;
      saveBtn.textContent = "Salvando...";
      statusEl.textContent = "";

      try {
        await api(`/api/teacher/student/${accessUserId}/access`, {
          method:  "PUT",
          body:    JSON.stringify({ slugs: selected }),
        });
        statusEl.textContent = `✓ ${selected.length} módulo(s) liberado(s)`;
        statusEl.className   = "access-save-status ok";
      } catch (err) {
        statusEl.textContent = "Erro ao salvar: " + err.message;
        statusEl.className   = "access-save-status error";
      } finally {
        saveBtn.disabled    = false;
        saveBtn.textContent = "Salvar acesso";
      }
    });
  }

  function groupIconHtml(group) {
    return group && group.icon_file
      ? `<img src="/static/icons/${group.icon_file}" alt="" class="access-group-icon">`
      : `${group ? group.icon : ""} `;
  }

  function closeAccessModal() {
    document.getElementById("access-backdrop").style.display = "none";
    accessUserId = null;
  }

  document.getElementById("cancel-access-btn").addEventListener("click", closeAccessModal);
  document.getElementById("access-backdrop").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeAccessModal();
  });

  // ── Init ──────────────────────────────────────────────────────────────────────

  await loadStudents();

})();
