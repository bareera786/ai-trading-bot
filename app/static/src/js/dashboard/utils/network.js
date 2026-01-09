export async function fetchJson(url, options = {}) {
  // Auto-reload when a new dashboard bundle is deployed.
  // This compares a hash of manifest.json and reloads the page if it changes.
  try {
    await maybeReloadOnNewManifest();
  } catch (e) {
    // Silent fail (offline / storage errors)
  }

  const response = await fetch(url, { credentials: 'same-origin', ...options });

  const contentType = (response.headers.get('content-type') || '').toLowerCase();
  const isJson = contentType.includes('application/json');

  // Surface auth redirects as a clear error instead of silently returning null.
  if (response.redirected && response.url && response.url.includes('/login')) {
    throw new Error('Authentication required');
  }

  // If the server returned a non-JSON body, treat it as an error for this helper.
  if (!isJson && response.status !== 204) {
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    throw new Error(`Expected JSON but got ${contentType || 'unknown content-type'}`);
  }

  let body = null;
  if (response.status !== 204) {
    try {
      body = await response.json();
    } catch (error) {
      console.warn('Failed to parse JSON', error);
      body = null;
    }
  }

  if (!response.ok) {
    const message = body?.error || body?.message || `Request failed: ${response.status}`;
    throw new Error(message);
  }

  return body;
}

let _lastManifestCheckAt = 0;

function hashStringDjb2(input) {
  let hash = 5381;
  for (let i = 0; i < input.length; i++) {
    hash = ((hash << 5) + hash) ^ input.charCodeAt(i);
  }
  // unsigned 32-bit
  return (hash >>> 0).toString(16);
}

async function maybeReloadOnNewManifest() {
  if (typeof window === 'undefined') return;

  // Prevent reload loops
  try {
    if (window.sessionStorage?.getItem('dashboard_reload_in_progress') === '1') {
      window.sessionStorage.removeItem('dashboard_reload_in_progress');
      return;
    }
  } catch (e) {}

  const now = Date.now();
  // Throttle manifest checks (max once per 60s)
  if (now - _lastManifestCheckAt < 60_000) return;
  _lastManifestCheckAt = now;

  let resp;
  try {
    resp = await fetch('/static/dist/manifest.json', { cache: 'no-store' });
  } catch (e) {
    return;
  }

  if (!resp || !resp.ok) return;

  let manifest;
  try {
    manifest = await resp.json();
  } catch (e) {
    return;
  }

  const json = JSON.stringify(manifest || {});
  const newHash = hashStringDjb2(json);

  try {
    const key = 'dashboard_manifest_hash';
    const prev = window.localStorage?.getItem(key);
    if (prev && prev !== newHash) {
      window.sessionStorage?.setItem('dashboard_reload_in_progress', '1');
      window.localStorage?.setItem(key, newHash);
      window.location.reload();
      return;
    }
    if (!prev) {
      window.localStorage?.setItem(key, newHash);
    }
  } catch (e) {
    // ignore storage failures
  }
}
