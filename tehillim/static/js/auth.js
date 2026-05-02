// ─── Auth — Supabase Magic Link + Sincronização de Progresso ─────────────────
// Depende de: @supabase/supabase-js CDN (window.supabase)
// Expõe: window.auth

(function () {

  let _resolveReady;
  const _readyPromise = new Promise((r) => { _resolveReady = r; });

  const Auth = {
    client:       null,
    session:      null,
    ready:          _readyPromise,
    _accessCache:   null,
    _accessCacheAt: 0,

    // ── Inicialização ─────────────────────────────────────────────────────────

    async init() {
      // Restaura sessão dev persistida no localStorage
      if (localStorage.getItem("tehillim:dev") === "1") {
        this.session = {
          user: {
            id: "dev-user-00000000-0000-0000-0000-000000000000",
            email: "dev@tehillim.dev",
            user_metadata: { name: "Dev", role: "teacher" },
          },
          access_token: "__dev__",
        };
        this._accessCache   = { slugs: new Set(), isTeacher: true };
        this._accessCacheAt = Date.now();
        document.cookie = `ta=${encodeURIComponent(JSON.stringify({ s: [], t: true }))}; path=/; max-age=3600; SameSite=Lax`;
        this._renderBadge();
        _resolveReady();
        return;
      }

      if (!window.SUPABASE_URL || !window.supabase) { _resolveReady(); return; }

      try {
        this.client = window.supabase.createClient(
          window.SUPABASE_URL,
          window.SUPABASE_ANON_KEY,
          { auth: { persistSession: true, autoRefreshToken: true } }
        );

        this.client.auth.onAuthStateChange(async (event, session) => {
          this.session = session;
          this._accessCache = null;
          this._renderBadge();
          if (event === "SIGNED_IN") {
            try { await this._onSignIn(); } catch (e) { console.error("[auth] _onSignIn:", e); }
            if (window.location.pathname === "/login") {
              window.location.href = "/";
            }
          }
        });

        const { data } = await this.client.auth.getSession();
        this.session = data.session;
        this._renderBadge();

        if (this.session) {
          await this._syncFromCloud();
          // Pré-popula cache de acesso antes de resolver ready
          // Se localStorage tiver dados válidos, retorna instantâneo; senão faz fetch
          await this.getAccess();
        }
      } catch (e) {
        console.error("[auth] init error:", e);
      } finally {
        _resolveReady();
      }
    },

    // ── API pública ───────────────────────────────────────────────────────────

    getUser() { return this.session?.user ?? null; },
    isLoggedIn() { return !!this.session; },
    getName() {
      const user = this.getUser();
      return user?.user_metadata?.name || user?.email?.split("@")[0] || "Aluno";
    },

    async updateName(name) {
      if (this.session?.access_token === "__dev__") {
        this.session = { ...this.session, user: { ...this.session.user, user_metadata: { ...this.session.user.user_metadata, name } } };
        this._renderBadge();
        return null;
      }
      if (!this.client) return;
      const { data, error } = await this.client.auth.updateUser({ data: { name } });
      if (!error && data.user) {
        this.session = { ...this.session, user: data.user };
        this._renderBadge();
      }
      return error ?? null;
    },

    async signInWithPassword(email, password) {
      // Modo dev: credenciais dev/dev criam sessão local sem Supabase
      if (email === "dev" && password === "dev") {
        localStorage.setItem("tehillim:dev", "1");
        this.session = {
          user: {
            id: "dev-user-00000000-0000-0000-0000-000000000000",
            email: "dev@tehillim.dev",
            user_metadata: { name: "Dev", role: "teacher" },
          },
          access_token: "__dev__",
        };
        this._accessCache   = { slugs: new Set(), isTeacher: true };
        this._accessCacheAt = Date.now();
        document.cookie = `ta=${encodeURIComponent(JSON.stringify({ s: [], t: true }))}; path=/; max-age=3600; SameSite=Lax`;
        this._renderBadge();
        window.location.href = "/";
        return null;
      }

      if (!this.client) return { message: "Supabase não inicializado." };
      const { error } = await this.client.auth.signInWithPassword({ email, password });
      return error ?? null;
    },

    async sendMagicLink(email) {
      if (!this.client) return { message: "Supabase não inicializado." };
      const { error } = await this.client.auth.signInWithOtp({
        email,
        options: { emailRedirectTo: window.location.origin },
      });
      return error ?? null;
    },

    async signOut() {
      localStorage.removeItem("tehillim:dev");
      localStorage.removeItem("tehillim:access");
      localStorage.removeItem("tehillim:streak");
      this.session = null;
      this._accessCache = null;
      if (this.client) await this.client.auth.signOut();
      window.location.href = "/logout";
    },

    async getAccess() {
      if (!this.isLoggedIn()) return { slugs: new Set(), isTeacher: false };
      const now = Date.now();

      // 1. Cache em memória (mesma página, < 60 s)
      if (this._accessCache !== null && now - this._accessCacheAt < 60_000) {
        return this._accessCache;
      }

      // 2. Cache no localStorage (entre páginas, < 5 min)
      try {
        const stored = JSON.parse(localStorage.getItem("tehillim:access") || "null");
        if (stored && now - stored.at < 300_000) {
          this._accessCache   = { slugs: new Set(stored.slugs), isTeacher: !!stored.isTeacher };
          this._accessCacheAt = stored.at;
          // Atualiza em segundo plano se cache > 60 s
          if (now - stored.at > 60_000) this._fetchAccess().catch(() => {});
          return this._accessCache;
        }
      } catch { /* ignora erro de parse */ }

      // 3. Busca no servidor
      return this._fetchAccess();
    },

    async _fetchAccess() {
      const token = this.session?.access_token;
      if (!token) return { slugs: new Set(), isTeacher: false };

      // Modo dev: bypassa chamada ao servidor
      if (token === "__dev__") {
        const devAccess = { slugs: new Set(), isTeacher: true };
        this._accessCache   = devAccess;
        this._accessCacheAt = Date.now();
        localStorage.setItem("tehillim:access", JSON.stringify({ slugs: [], isTeacher: true, at: Date.now() }));
        document.cookie = `ta=${encodeURIComponent(JSON.stringify({ s: [], t: true }))}; path=/; max-age=300; SameSite=Lax`;
        return devAccess;
      }

      try {
        const r    = await fetch("/api/my-access", { headers: { "Authorization": `Bearer ${token}` } });
        const data = r.ok ? await r.json() : null;
        if (data) {
          this._accessCache   = { slugs: new Set(data.slugs), isTeacher: !!data.isTeacher };
          this._accessCacheAt = Date.now();
          const stored = { slugs: data.slugs, isTeacher: !!data.isTeacher, at: Date.now() };
          localStorage.setItem("tehillim:access", JSON.stringify(stored));
          // Cookie lido pelo servidor para renderizar o estado correto sem delay
          document.cookie = `ta=${encodeURIComponent(JSON.stringify({ s: data.slugs, t: !!data.isTeacher }))}; path=/; max-age=300; SameSite=Lax`;
        }
      } catch { /* mantém cache anterior se houver */ }
      return this._accessCache ?? { slugs: new Set(), isTeacher: false };
    },

    // Salva progresso de um módulo (chamado pelo app.js)
    async saveProgress(moduleSlug, completed) {
      if (!this.isLoggedIn() || this.session?.access_token === "__dev__") return;
      await this.client.from("module_progress").upsert(
        { user_id: this.session.user.id, module_slug: moduleSlug, completed, updated_at: new Date().toISOString() },
        { onConflict: "user_id,module_slug" }
      );
    },

    // Registra o dia de estudo atual
    async markStudyDay() {
      if (!this.isLoggedIn() || this.session?.access_token === "__dev__") return;
      const day = new Date().toISOString().split("T")[0];
      await this.client.from("study_days").upsert(
        { user_id: this.session.user.id, day },
        { onConflict: "user_id,day", ignoreDuplicates: true }
      );
    },

    // ── Sincronização localStorage ↔ Supabase ─────────────────────────────────

    async _onSignIn() {
      this._accessCache = null;
      localStorage.removeItem("tehillim:access");
      localStorage.removeItem("tehillim:last-sync");
      localStorage.removeItem("tehillim:streak");
      await this._syncFromCloud();
      await this.markStudyDay();
      // Pré-busca acesso e salva no localStorage — próximas páginas carregam instantaneamente
      await this._fetchAccess();
    },

    // Baixa progresso da nuvem e faz merge com localStorage (max wins)
    // Executa no máximo uma vez a cada 5 minutos para evitar fetches repetidos
    async _syncFromCloud() {
      if (!this.isLoggedIn() || this.session?.access_token === "__dev__") return;

      const lastSync = Number(localStorage.getItem("tehillim:last-sync") || 0);
      if (Date.now() - lastSync < 5 * 60_000) {
        // Ainda dentro do TTL — só sobe o que há em localStorage (sem fetch)
        await this._pushToCloud();
        return;
      }

      const { data } = await this.client
        .from("module_progress")
        .select("module_slug, completed")
        .eq("user_id", this.session.user.id);

      if (data) {
        localStorage.setItem("tehillim:last-sync", String(Date.now()));
        for (const row of data) {
          const key   = `tehillim:${row.module_slug}:completed`;
          const local = Number(localStorage.getItem(key) || 0);
          localStorage.setItem(key, String(Math.max(local, row.completed)));
        }
      }

      // Sobe progresso local que a nuvem ainda não tem
      await this._pushToCloud();
    },

    // Envia progresso local para a nuvem
    async _pushToCloud() {
      if (!this.isLoggedIn() || this.session?.access_token === "__dev__") return;
      const rows = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key?.startsWith("tehillim:") || !key.endsWith(":completed")) continue;
        const slug      = key.split(":")[1];
        const completed = Number(localStorage.getItem(key) || 0);
        if (completed > 0) rows.push({ user_id: this.session.user.id, module_slug: slug, completed });
      }
      if (rows.length) {
        await this.client.from("module_progress").upsert(rows, { onConflict: "user_id,module_slug" });
      }
    },

    // ── UI ────────────────────────────────────────────────────────────────────

    _renderBadge() {
      const badge = document.getElementById("auth-badge");
      if (!badge) return;
      if (this.session) {
        const name  = this.getName();
        const email = this.session.user.email;
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
  document.addEventListener("DOMContentLoaded", () => Auth.init());

})();
