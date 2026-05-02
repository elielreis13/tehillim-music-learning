// ─── Note table (octave 4, equal temperament) ─────────────────────────────────

const NOTE_FREQUENCIES = {
  // Português
  "Dó":   261.63, "Ré":   293.66, "Mi":   329.63,
  "Fá":   349.23, "Sol":  392.00, "Lá":   440.00,
  "Si":   493.88, "Dó5":  523.25,
  // English (memory game pairs etc.)
  "C":    261.63, "D":    293.66, "E":    329.63,
  "F":    349.23, "G":    392.00, "A":    440.00,
  "B":    493.88, "C5":   523.25,
};

// ─── Engine ───────────────────────────────────────────────────────────────────

class AudioEngine {
  constructor() {
    this._ctx = null;
  }

  // Lazy-create AudioContext on first user interaction (browser requirement)
  get ctx() {
    if (!this._ctx) {
      this._ctx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (this._ctx.state === "suspended") this._ctx.resume();
    return this._ctx;
  }

  // ── Core: play a single frequency ──────────────────────────────────────────

  _playFreq(freq, duration = 0.6, volume = 0.45, delaySeconds = 0) {
    const ctx = this.ctx;
    const now = ctx.currentTime + delaySeconds;

    // Main oscillator (triangle = warm, flute-like)
    const osc1  = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = "triangle";
    osc1.frequency.value = freq;

    // Harmonic at 2× frequency (adds piano-like brightness, quieter)
    const osc2  = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = "sine";
    osc2.frequency.value = freq * 2;

    // Piano-style ADSR: fast attack, exponential decay, no sustain, short release
    gain1.gain.setValueAtTime(0, now);
    gain1.gain.linearRampToValueAtTime(volume, now + 0.008);
    gain1.gain.exponentialRampToValueAtTime(volume * 0.55, now + 0.12);
    gain1.gain.exponentialRampToValueAtTime(0.001, now + duration);

    gain2.gain.setValueAtTime(0, now);
    gain2.gain.linearRampToValueAtTime(volume * 0.18, now + 0.008);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + duration * 0.5);

    osc1.connect(gain1); gain1.connect(ctx.destination);
    osc2.connect(gain2); gain2.connect(ctx.destination);

    osc1.start(now); osc1.stop(now + duration + 0.05);
    osc2.start(now); osc2.stop(now + duration * 0.5 + 0.05);
  }

  // ── Public API ─────────────────────────────────────────────────────────────

  /** Play a note by name ("Dó", "Sol", "C", "G"…) or by Hz. */
  playNote(nameOrHz, duration = 0.6) {
    const freq = typeof nameOrHz === "number"
      ? nameOrHz
      : NOTE_FREQUENCIES[nameOrHz];
    if (freq) this._playFreq(freq, duration);
  }

  /** Play an array of note names in sequence. */
  playScale(names, intervalMs = 420) {
    names.forEach((name, i) => {
      const freq = NOTE_FREQUENCIES[name];
      if (freq) this._playFreq(freq, 0.55, 0.4, i * intervalMs / 1000);
    });
  }

  /** Play only the known notes of a sequence (skips blanks marked "?"). */
  playSequenceWithGap(names, intervalMs = 480) {
    names.forEach((name, i) => {
      if (name === "?") return;
      const freq = NOTE_FREQUENCIES[name];
      if (freq) this._playFreq(freq, 0.55, 0.4, i * intervalMs / 1000);
    });
  }

  /** Play a rhythmic pattern: array of 1/0 (1 = tap, 0 = rest). */
  playRhythm(pattern, intervalMs = 600) {
    const freq = NOTE_FREQUENCIES["Dó"];
    pattern.forEach((beat, i) => {
      if (beat) this._playFreq(freq, 0.15, 0.5, i * intervalMs / 1000);
    });
  }

  /** Play a short percussion tick (for rhythm-tap beat indicator). */
  tick(strong = true) {
    this._playFreq(strong ? 880 : 440, 0.06, strong ? 0.35 : 0.15);
  }

  /** Play success chord (C major arpeggio). */
  correct() {
    [261.63, 329.63, 392.00, 523.25].forEach((freq, i) => {
      this._playFreq(freq, 0.4, 0.28, i * 0.07);
    });
  }

  /** Play a short descending fail sound. */
  wrong() {
    this._playFreq(220, 0.35, 0.3);
  }

  /** Returns true if the name is a known note. */
  isNote(name) {
    return name in NOTE_FREQUENCIES;
  }
}

// ─── Singleton ────────────────────────────────────────────────────────────────

window.audio = new AudioEngine();
