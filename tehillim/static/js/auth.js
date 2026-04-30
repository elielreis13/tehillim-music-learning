(function () {
  'use strict';

  let _client  = null;
  let _session = null;
  let _accessCache = null;
  let _resolveReady;

  const ready = new Promise(resolve => { _resolveReady = resolve; });

  async function init() {
    _client = window.supabase.createClient(window.SUPABASE_URL, window.SUPABASE_ANON_KEY);

    const { data: { session } } = await _client.auth.getSession();
    _session = session;

    if (_session) {
      await _fetchAccess();
      _syncFromCloud().catch(() => {});
    }

    _client.auth.onAuthStateChange((_event, session) => {
      _session = session;
    });

    _resolveReady();
  }

  async function signInWithPassword(email, password) {
    const { data, error } = await _client.auth.signInWithPassword({ email, password });
    if (error) throw error;
    _session = data.session;
    await _fetchAccess();
    return data;
  }

  async function sendMagicLink(email) {
    const { error } = await _client.auth.signInWithOtp({
      email,
      options: { shouldCreateUser: false },
    });
    if (error) throw error;
  }

  async function signOut() {
    document.cookie = 'ta=; max-age=0; path=/';
    localStorage.removeItem('tehillim:access');
    localStorage.removeItem('tehillim:last-sync');
    localStorage.removeItem('tehillim:streak');
    _accessCache = null;
    await _client.auth.signOut();
    _session = null;
    window.location.href = '/login';
  }

  async function getAccess() {
    if (_accessCache && Date.now() - _accessCache.at < 60_000) {
      return { slugs: _accessCache.slugs, isTeacher: _accessCache.isTeacher };
    }
    try {
      const raw = localStorage.getItem('tehillim:access');
      if (raw) {
        const data = JSON.parse(raw);
        if (Date.now() - data.at < 5 * 60_000) {
          _accessCache = { ...data, slugs: new Set(data.slugs) };
          return { slugs: _accessCache.slugs, isTeacher: _accessCache.isTeacher };
        }
      }
    } catch {}
    return _fetchAccess();
  }

  async function _fetchAccess() {
    if (!_session) return { slugs: new Set(), isTeacher: false };
    try {
      const res = await fetch('/api/my-access', {
        headers: { Authorization: `Bearer ${_session.access_token}` },
      });
      const data = await res.json();
      const slugs     = new Set(data.slugs || []);
      const isTeacher = Boolean(data.isTeacher);

      const cookieVal = encodeURIComponent(JSON.stringify({ s: [...slugs], t: isTeacher }));
      document.cookie = `ta=${cookieVal}; path=/; max-age=${60 * 60 * 24}`;

      _accessCache = { slugs, isTeacher, at: Date.now() };
      localStorage.setItem('tehillim:access', JSON.stringify({
        slugs: [...slugs], isTeacher, at: Date.now(),
      }));
      return { slugs, isTeacher };
    } catch {
      return { slugs: new Set(), isTeacher: false };
    }
  }

  async function _syncFromCloud() {
    if (!_session) return;
    const FIVE_MIN = 5 * 60_000;
    const lastSync = Number(localStorage.getItem('tehillim:last-sync') || 0);
    if (Date.now() - lastSync < FIVE_MIN) return;

    try {
      const { data } = await _client
        .from('module_progress')
        .select('module_slug,completed')
        .eq('user_id', _session.user.id);

      (data || []).forEach(row => {
        const key   = `tehillim:${row.module_slug}:completed`;
        const local = Number(localStorage.getItem(key) || 0);
        if (row.completed > local) localStorage.setItem(key, row.completed);
      });

      localStorage.setItem('tehillim:last-sync', Date.now());
    } catch {}
  }

  async function saveProgress(slug, completed) {
    localStorage.setItem(`tehillim:${slug}:completed`, completed);
    if (!_session) return;
    try {
      await _client.from('module_progress').upsert(
        { user_id: _session.user.id, module_slug: slug, completed, updated_at: new Date().toISOString() },
        { onConflict: 'user_id,module_slug' },
      );
    } catch {}
  }

  async function markStudyDay() {
    if (!_session) return;
    const today = new Date().toISOString().slice(0, 10);
    try {
      await _client.from('study_days').upsert(
        { user_id: _session.user.id, day: today },
        { onConflict: 'user_id,day', ignoreDuplicates: true },
      );
    } catch {}
  }

  function isLoggedIn() { return Boolean(_session); }

  function getName() {
    return (
      _session?.user?.user_metadata?.name ||
      _session?.user?.email?.split('@')[0] ||
      ''
    );
  }

  window.auth = {
    ready,
    signInWithPassword,
    sendMagicLink,
    signOut,
    getAccess,
    saveProgress,
    markStudyDay,
    isLoggedIn,
    getName,
  };

  Object.defineProperty(window.auth, 'session', { get: () => _session });
  Object.defineProperty(window.auth, 'client',  { get: () => _client  });

  init();
})();
