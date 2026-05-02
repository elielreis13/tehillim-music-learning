// ─── Group page — estado inicial via servidor, atualizações dinâmicas via JS ──

(async function () {
  const cards = document.querySelectorAll(".module-card");
  if (!cards.length) return;

  // Adiciona listener universal em todos os cards
  cards.forEach((card) => {
    card.addEventListener("click", _onCardClick);
  });

  // Re-aplica acesso quando o token for renovado ou o usuário fizer login
  await Promise.race([
    window.auth?.ready ?? Promise.resolve(),
    new Promise((r) => setTimeout(r, 5000)),
  ]);

  if (window.auth?.client) {
    window.auth.client.auth.onAuthStateChange(async (event) => {
      if (event === "TOKEN_REFRESHED" || event === "SIGNED_IN") {
        if (window.auth) {
          window.auth._accessCache   = null;
          window.auth._accessCacheAt = 0;
        }
        await _applyAccess();
      }
    });
  }

  // ── Funções ───────────────────────────────────────────────────────────────

  async function _applyAccess() {
    if (!window.auth?.isLoggedIn()) return;
    const access = await window.auth.getAccess();
    if (access.isTeacher) {
      cards.forEach(_unlockCard);
      return;
    }
    cards.forEach((card) => {
      const slug = card.dataset.href.split("/modulos/")[1];
      if (slug && access.slugs.has(slug)) _unlockCard(card);
    });
  }

  async function _onCardClick(e) {
    const card = e.currentTarget;
    if (card.dataset.unlocked === "true") return;

    e.preventDefault();

    if (window.auth) window.auth._accessCache = null;

    const loggedIn = window.auth?.isLoggedIn() ?? false;
    if (!loggedIn) {
      _showToast("Faça login para acessar os módulos.");
      return;
    }

    const fresh = await window.auth.getAccess();
    const slug  = card.dataset.href.split("/modulos/")[1];
    if (slug && (fresh?.isTeacher || fresh?.slugs.has(slug))) {
      _unlockCard(card);
      window.location.href = card.dataset.href;
    } else {
      _showToast("Este módulo ainda não foi liberado pelo seu professor.");
    }
  }

  function _unlockCard(card) {
    card.dataset.unlocked = "true";
    card.classList.remove("module-locked-card");
    card.removeAttribute("aria-disabled");
    card.setAttribute("href", card.dataset.href);
    const badge = card.querySelector(".module-lock-badge");
    if (badge) badge.remove();
  }

  function _showToast(message) {
    const existing = document.getElementById("group-toast");
    if (existing) existing.remove();
    const toast = document.createElement("div");
    toast.id        = "group-toast";
    toast.className = "group-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("group-toast-show"));
    setTimeout(() => {
      toast.classList.remove("group-toast-show");
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }
})();
