// ─── Recorder — MediaRecorder + Supabase Storage ─────────────────────────────
// Depende de: auth.js (window.auth)
// Expõe: window.recorder

(function () {

  const Recorder = {
    _chunks:      [],
    _stream:      null,
    _mr:          null,
    isRecording:  false,

    // ── Gravação ──────────────────────────────────────────────────────────────

    async start() {
      if (this.isRecording) return;
      this._chunks = [];

      try {
        this._stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        throw new Error("Permissão de microfone negada ou indisponível.");
      }

      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/ogg";
      this._mr   = new MediaRecorder(this._stream, { mimeType: mime });
      this._mr.ondataavailable = (e) => { if (e.data.size > 0) this._chunks.push(e.data); };
      this._mr.start(200);
      this.isRecording = true;
    },

    stop() {
      return new Promise((resolve, reject) => {
        if (!this._mr) { reject(new Error("Gravação não iniciada.")); return; }
        this._mr.onstop = () => {
          const mime = this._mr.mimeType || "audio/webm";
          const blob = new Blob(this._chunks, { type: mime });
          this._stream?.getTracks().forEach((t) => t.stop());
          this.isRecording = false;
          resolve(blob);
        };
        this._mr.stop();
      });
    },

    // ── Upload para Supabase Storage ──────────────────────────────────────────

    async upload(blob, moduleSlug) {
      const user = window.auth?.getUser();
      if (!user) throw new Error("Faça login para enviar gravações.");

      const client = window.auth.client;
      if (!client) throw new Error("Supabase não configurado.");

      const token = window.auth.session?.access_token;
      if (!token) throw new Error("Sessão expirada. Faça login novamente.");

      const ext      = blob.type.includes("ogg") ? "ogg" : "webm";
      const filename = `${user.id}/${moduleSlug}/${Date.now()}.${ext}`;
      const uploadUrl = `${client.storageUrl}/object/recordings/${filename}`;

      const res = await fetch(uploadUrl, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "x-upsert": "false",
          "Content-Type": blob.type,
        },
        body: blob,
      });

      if (!res.ok) {
        const body = await res.text().catch(() => res.statusText);
        throw new Error(`Falha no upload: ${res.status} — ${body}`);
      }

      const data = await res.json();
      const audioPath = data.Key ?? data.path ?? filename;

      // Registra submission no banco (não-fatal)
      client.from("submissions").insert({
        user_id:     user.id,
        module_slug: moduleSlug,
        audio_path:  audioPath,
      });

      return audioPath;
    },

    // ── UI helper — cria bloco de gravação pronto para uso ────────────────────
    // Retorna um elemento <div> com os botões e preview.
    // onUpload(path) é chamado quando o upload terminar com sucesso.

    createWidget(moduleSlug, { onUpload } = {}) {
      const wrap = document.createElement("div");
      wrap.className = "recorder-widget";
      wrap.innerHTML = `
        <div class="rec-actions">
          <button class="rec-start secondary-btn">🎤 Gravar prática</button>
          <label class="rec-file-label secondary-btn">
            📁 Enviar arquivo
            <input type="file" class="rec-file-input" accept="audio/*" style="display:none">
          </label>
          <button class="rec-stop secondary-btn" style="display:none">⏹ Parar gravação</button>
        </div>
        <div class="rec-preview" style="display:none">
          <audio controls class="rec-audio"></audio>
          <div class="rec-preview-actions">
            <button class="rec-upload secondary-btn">☁ Enviar ao professor</button>
            <button class="rec-redo   secondary-btn">⟳ Regravar</button>
          </div>
          <p class="rec-status" aria-live="polite"></p>
        </div>
      `;

      const btnStart  = wrap.querySelector(".rec-start");
      const btnStop   = wrap.querySelector(".rec-stop");
      const fileInput = wrap.querySelector(".rec-file-input");
      const preview   = wrap.querySelector(".rec-preview");
      const audio     = wrap.querySelector(".rec-audio");
      const btnUpload = wrap.querySelector(".rec-upload");
      const btnRedo   = wrap.querySelector(".rec-redo");
      const recActions = wrap.querySelector(".rec-actions");
      const status    = wrap.querySelector(".rec-status");

      let currentBlob = null;

      function showPreview(blob) {
        currentBlob = blob;
        audio.src   = URL.createObjectURL(blob);
        recActions.style.display = "none";
        preview.style.display    = "";
        status.textContent       = "";
        btnUpload.disabled       = false;
        btnUpload.style.display  = "";
      }

      btnStart.addEventListener("click", async () => {
        status.textContent = "";
        try {
          await Recorder.start();
          btnStart.style.display       = "none";
          wrap.querySelector(".rec-file-label").style.display = "none";
          btnStop.style.display        = "";
        } catch (e) {
          status.textContent = e.message;
        }
      });

      btnStop.addEventListener("click", async () => {
        const blob = await Recorder.stop();
        showPreview(blob);
      });

      fileInput.addEventListener("change", () => {
        const file = fileInput.files[0];
        if (!file) return;
        showPreview(file);
      });

      btnRedo.addEventListener("click", () => {
        currentBlob = null;
        audio.src   = "";
        fileInput.value          = "";
        preview.style.display    = "none";
        recActions.style.display = "";
        btnStart.style.display   = "";
        wrap.querySelector(".rec-file-label").style.display = "";
        btnStop.style.display    = "none";
        status.textContent       = "";
      });

      btnUpload.addEventListener("click", async () => {
        if (!currentBlob) return;
        btnUpload.disabled  = true;
        status.textContent  = "Enviando...";
        status.className    = "rec-status";
        try {
          const path = await Recorder.upload(currentBlob, moduleSlug);
          status.textContent  = "✓ Enviado com sucesso!";
          status.className    = "rec-status ok";
          btnUpload.style.display = "none";
          onUpload?.(path);
        } catch (e) {
          status.textContent = "Não foi possível enviar a gravação. Por favor, entre em contato com o professor.";
          status.className   = "rec-status error";
          btnUpload.disabled = false;
          console.error("[recorder] upload error:", e);
        }
      });

      return wrap;
    },
  };

  window.recorder = Recorder;

})();
