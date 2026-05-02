// VexFlow 3.x utilities — requires vexflow-min.js loaded before this file
// Global exposed: window.VFUtils

(function () {

  const PT_TO_KEY = {
    "Dó": "c", "Ré": "d", "Mi": "e",
    "Fá": "f", "Sol": "g", "Lá": "a", "Si": "b",
  };

  const FIGURE_TO_DUR = {
    "Semibreve": "w", "Mínima": "h", "Semínima": "q",
    "Colcheia": "8", "Semicolcheia": "16",
  };

  const DUR_BEATS = { "w": 4, "h": 2, "q": 1, "8": 0.5, "16": 0.25 };

  function VF() {
    return window.Vex && window.Vex.Flow;
  }

  function isReady() {
    return !!VF();
  }

  // Returns { vf, ctx, staveW } or null
  function _setup(id, height) {
    const vf = VF();
    const el = document.getElementById(id);
    if (!vf || !el) return null;

    el.innerHTML = "";
    const totalW = Math.max(el.offsetWidth || 420, 260);

    const renderer = new vf.Renderer(el, vf.Renderer.Backends.SVG);
    renderer.resize(totalW, height);
    const ctx = renderer.getContext();
    ctx.setFont("Arial", 10, "");

    return { vf, ctx, totalW };
  }

  function _stave(vf, ctx, x, y, w, clef, timeSig) {
    const stave = new vf.Stave(x, y, w);
    if (clef)    stave.addClef(clef);
    if (timeSig) stave.addTimeSignature(timeSig);
    stave.setContext(ctx).draw();
    return stave;
  }

  function _voice(vf, notes, numBeats) {
    const voice = new vf.Voice({ num_beats: Math.max(numBeats, 1), beat_value: 4 });
    voice.setStrict(false);
    voice.addTickables(notes);
    return voice;
  }

  function _format(vf, voice, availableWidth) {
    new vf.Formatter().joinVoices([voice]).format([voice], availableWidth);
  }

  // ── Public API ────────────────────────────────────────────────────────────────

  function renderBlank(id, { height = 130, timeSig = "4/4" } = {}) {
    const s = _setup(id, height);
    if (!s) return;
    _stave(s.vf, s.ctx, 10, 30, s.totalW - 20, "treble", timeSig);
  }

  // ptNames: ["Dó","Ré","Mi",…]  as quarter notes on a single staff
  function renderScale(id, ptNames, octave = 4, { height = 130 } = {}) {
    const s = _setup(id, height);
    if (!s) return;
    const notes = ptNames
      .filter((n) => PT_TO_KEY[n])
      .map((n) => new s.vf.StaveNote({ keys: [`${PT_TO_KEY[n]}/${octave}`], duration: "q" }));
    if (!notes.length) { _stave(s.vf, s.ctx, 10, 30, s.totalW - 20, "treble", null); return; }
    const stave = _stave(s.vf, s.ctx, 10, 30, s.totalW - 20, "treble", `${notes.length}/4`);
    const voice = _voice(s.vf, notes, notes.length);
    _format(s.vf, voice, stave.getWidth() - 50);
    voice.draw(s.ctx, stave);
  }

  // pattern: [1, 0, 1, 1, …]  1=nota, 0=pausa
  function renderRhythm(id, pattern, { height = 130 } = {}) {
    const s = _setup(id, height);
    if (!s) return;
    const notes = pattern.map((b) =>
      new s.vf.StaveNote({ keys: ["b/4"], duration: b ? "q" : "qr" })
    );
    const stave = _stave(s.vf, s.ctx, 10, 30, s.totalW - 20, "treble", `${pattern.length}/4`);
    const voice = _voice(s.vf, notes, pattern.length);
    _format(s.vf, voice, stave.getWidth() - 50);
    voice.draw(s.ctx, stave);
  }

  // figures: [{ name: "Mínima" }, …]  builds a measure as it fills
  function renderMeasure(id, figures, targetBeats = 4, { height = 130 } = {}) {
    if (!figures.length) { renderBlank(id, { timeSig: `${targetBeats}/4`, height }); return; }
    const s = _setup(id, height);
    if (!s) return;
    const notes = figures.map((f) => {
      const dur = FIGURE_TO_DUR[f.name] || "q";
      return new s.vf.StaveNote({ keys: ["c/4"], duration: dur });
    });
    const stave = _stave(s.vf, s.ctx, 10, 30, s.totalW - 20, "treble", `${targetBeats}/4`);
    const voice = _voice(s.vf, notes, targetBeats);
    _format(s.vf, voice, stave.getWidth() - 50);
    voice.draw(s.ctx, stave);
  }

  // vfKeys: array of VexFlow keys e.g. ["c/4","e/4","g/4"] rendered as quarter notes
  function renderKeys(id, vfKeys, { height = 130 } = {}) {
    if (!vfKeys || !vfKeys.length) { renderBlank(id, { timeSig: null, height }); return; }
    const s = _setup(id, height);
    if (!s) return;
    const notes = vfKeys.map((k) => new s.vf.StaveNote({ keys: [k], duration: "q" }));
    const stave = _stave(s.vf, s.ctx, 10, 30, s.totalW - 20, "treble", null);
    const voice = _voice(s.vf, notes, notes.length);
    _format(s.vf, voice, stave.getWidth() - 50);
    voice.draw(s.ctx, stave);
  }

  // vfKey e.g. "c/4", duration e.g. "w"
  function renderNote(id, vfKey, duration = "w", { height = 130 } = {}) {
    const s = _setup(id, height);
    if (!s) return;
    const note  = new s.vf.StaveNote({ keys: [vfKey], duration });
    const stave = _stave(s.vf, s.ctx, 10, 30, s.totalW - 20, "treble", null);
    const voice = _voice(s.vf, [note], DUR_BEATS[duration] || 1);
    _format(s.vf, voice, stave.getWidth() - 50);
    voice.draw(s.ctx, stave);
  }

  // figures: [{ name: "Semibreve", beats: 4 }, …]  side-by-side
  function renderFigureShowcase(id, figures, { height = 130 } = {}) {
    const vf = VF();
    const el = document.getElementById(id);
    if (!vf || !el || !figures.length) return;

    el.innerHTML = "";
    const totalW = Math.max(el.offsetWidth || 420, figures.length * 80);
    const perW   = Math.floor(totalW / figures.length);

    const renderer = new vf.Renderer(el, vf.Renderer.Backends.SVG);
    renderer.resize(totalW, height);
    const ctx = renderer.getContext();
    ctx.setFont("Arial", 10, "");

    figures.forEach((f, i) => {
      const dur    = FIGURE_TO_DUR[f.name] || "q";
      const beats  = DUR_BEATS[dur] || 1;
      const stave  = new vf.Stave(i * perW + 4, 30, perW - 8);
      if (i === 0) stave.addClef("treble");
      stave.setContext(ctx).draw();

      const note  = new vf.StaveNote({ keys: ["c/4"], duration: dur });
      const voice = new vf.Voice({ num_beats: Math.max(beats, 1), beat_value: 4 });
      voice.setStrict(false);
      voice.addTickables([note]);
      new vf.Formatter().joinVoices([voice]).format([voice], perW - 40);
      voice.draw(ctx, stave);

      ctx.save();
      ctx.setFont("Arial", 9, "");
      ctx.fillText(f.name, i * perW + 8, height - 8);
      ctx.restore();
    });
  }

  function ptToKey(ptName, octave = 4) {
    const k = PT_TO_KEY[ptName];
    return k ? `${k}/${octave}` : null;
  }

  window.VFUtils = {
    isReady,
    renderBlank,
    renderScale,
    renderKeys,
    renderRhythm,
    renderMeasure,
    renderNote,
    renderFigureShowcase,
    ptToKey,
  };

})();
