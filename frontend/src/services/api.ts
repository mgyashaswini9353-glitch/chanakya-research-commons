const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

export function getToken(): string | null {
  return localStorage.getItem('crc_token');
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem('crc_token', token);
  else localStorage.removeItem('crc_token');
}

export async function apiRequest<T = any>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const err = await res.json();
      msg = err.detail || err.message || msg;
    } catch {
      // ignore json parse error
    }
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  get: <T = any>(path: string) => apiRequest<T>(path, { method: 'GET' }),
  post: <T = any>(path: string, body?: any) =>
    apiRequest<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),
  patch: <T = any>(path: string, body?: any) =>
    apiRequest<T>(path, { method: 'PATCH', body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: <T = any>(path: string) => apiRequest<T>(path, { method: 'DELETE' }),
};
