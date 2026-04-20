// In development, VITE_API_BASE_URL is unset and Vite proxies requests.
// In production (Vercel), set VITE_API_BASE_URL to your backend origin, e.g. http://52.15.49.162:8000
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '';

if (!BASE_URL && import.meta.env.PROD) {
  console.error(
    '[api] VITE_API_BASE_URL is not set. All API requests will hit the Vercel origin and return HTML instead of JSON. ' +
    'Add VITE_API_BASE_URL to your Vercel environment variables.'
  );
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch {
    throw new ApiError(0, 'Cannot reach the server. Make sure the backend is running.');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    let message = res.statusText;
    if (body.detail) {
      message = typeof body.detail === 'string'
        ? body.detail
        : body.detail[0]?.msg ?? res.statusText;
    }
    throw new ApiError(res.status, message);
  }

  return res.json();
}

export const api = {
  health: () =>
    request('/health'),

  seasons: () =>
    request('/seasons'),

  aiParse: (query) =>
    request('/ai/parse', {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),

  query: (params) =>
    request('/query', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  metrics: (params) =>
    request('/metrics', {
      method: 'POST',
      body: JSON.stringify(params),
    }),
};
