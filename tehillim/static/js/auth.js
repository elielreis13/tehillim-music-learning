// ─── Auth — sessão gerenciada pelo Flask ──────────────────────────────────────
// window.CURRENT_USER é injetado pelo servidor em cada página do app.
// Não há cliente Supabase no browser — sem chamadas de rede no carregamento.

(function () {

  const Auth = {
    // Compatibilidade: ready resolve instantaneamente
    ready: Promise.resolve(),

    // Compatibilidade: session.access_token não é mais usado pelo JS do app
    get session() {
      return window.CURRENT_USER ? { user: window.CURRENT_USER, access_token: null } : null;
    },

    isLoggedIn() { return !!window.CURRENT_USER; },
    getUser()    { return window.CURRENT_USER ?? null; },
    getName()    { return window.CURRENT_USER?.name || "Aluno"; },

    async updateName(name) {
      const r = await fetch("/api/me/name", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (r.ok) {
        window.CURRENT_USER = { ...window.CURRENT_USER, name };
        this._renderBadge();
      }
    },

    async signOut() {
      window.location.href = "/logout";
    },

    // Salva progresso via Flask (chama Supabase server-side com service key)
    async saveProgress(moduleSlug, completed) {
      if (!this.isLoggedIn()) return;
      fetch("/api/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ module_slug: moduleSlug, completed }),
      }).catch(() => {});
    },

    async markStudyDay() {
      if (!this.isLoggedIn()) return;
      fetch("/api/study-day", { method: "POST" }).catch(() => {});
    },

    // ── UI ──────────────────────────────────────────────────────────────────

    _renderBadge() {
      const badge = document.getElementById("auth-badge");
      if (!badge) return;
      if (window.CURRENT_USER) {
        const name  = this.getName();
        const email = window.CURRENT_USER.email || "";
        badge.innerHTML = `
          <div class="auth-user-wrap">
            <button class="auth-name-btn" title="${email}" id="auth-name-btn">${name}</button>
            <div class="auth-dropdown" id="auth-dropdown" style="display:none">
              <form class="auth-name-form" id="auth-name-form">
                <input class="auth-name-input" id="auth-name-input"
                       type="text" value="${name}" placeholder="Seu nome" maxlength="40" />
                <button type="submit" class="auth-name-save">Salvar</button>
              </form>
              <hr class="auth-sep">
              <button class="auth-logout" onclick="window.auth.signOut()">Sair</button>
            </div>
          </div>
        `;

        const btn      = badge.querySelector("#auth-name-btn");
        const dropdown = badge.querySelector("#auth-dropdown");
        const form     = badge.querySelector("#auth-name-form");

        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          const open = dropdown.style.display !== "none";
          dropdown.style.display = open ? "none" : "";
          if (!open) badge.querySelector("#auth-name-input").focus();
        });

        document.addEventListener("click", (e) => {
          if (!badge.contains(e.target)) dropdown.style.display = "none";
        }, { capture: true });

        form.addEventListener("submit", async (e) => {
          e.preventDefault();
          const newName = badge.querySelector("#auth-name-input").value.trim();
          if (!newName) return;
          const saveBtn = form.querySelector(".auth-name-save");
          saveBtn.disabled = true;
          await window.auth.updateName(newName);
          saveBtn.disabled = false;
          dropdown.style.display = "none";
        });
      } else {
        badge.innerHTML = `<a class="auth-login-link" href="/login">Entrar</a>`;
      }
    },
  };

  window.auth = Auth;
  document.addEventListener("DOMContentLoaded", () => Auth._renderBadge());

})();
