import { apiUrl } from '../lib/apiClient';

const API_PREFIX = '/api/v1';

export class ApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch(apiUrl(`${API_PREFIX}${path}`), {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  if (!res.ok) {
    let code = 'unknown_error';
    let msg = res.statusText;
    try {
      const err = await res.json();
      code = err?.error?.code ?? code;
      msg = err?.error?.message ?? msg;
    } catch {}
    throw new ApiError(code, msg, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) =>
    request<T>('GET', path, undefined, signal),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body?: unknown) => request<T>('PATCH', path, body),
  delete: <T>(path: string) => request<T>('DELETE', path),
};

export type SseCleanup = () => void;

export function openSse(
  path: string,
  onMessage: (data: unknown) => void,
  onError?: (err: Event) => void,
): SseCleanup {
  const es = new EventSource(apiUrl(`${API_PREFIX}${path}`));
  es.onmessage = (e) => {
    try {
      onMessage(JSON.parse(e.data));
    } catch {}
  };
  if (onError) es.onerror = onError;
  return () => es.close();
}
