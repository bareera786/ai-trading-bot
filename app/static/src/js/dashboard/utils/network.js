export async function fetchJson(url, options = {}) {
  const response = await fetch(url, { credentials: 'same-origin', ...options });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  try {
    return await response.json();
  } catch (error) {
    console.warn('Failed to parse JSON', error);
    return null;
  }
}
