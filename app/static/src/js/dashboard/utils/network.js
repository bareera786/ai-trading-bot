export async function fetchJson(url, options = {}) {
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
