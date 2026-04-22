/**
 * Thin helpers that prepend the backend base URL (from backendPort.ts)
 * to API paths and wrap `fetch()` / `EventSource` so existing screens
 * can be migrated with a single-word rename (`fetch` → `apiFetch`).
 *
 * In dev the base is "", so `apiUrl("/api/v1/foo")` returns "/api/v1/foo"
 * and the Vite proxy handles it. In Tauri production the base is
 * "http://127.0.0.1:<port>", so the same input returns a full URL.
 */
import { getBackendBase, resolveBackendBase } from "./backendPort";

/** Prefix `path` with the backend base URL. Synchronous; callers must
 *  have already awaited `resolveBackendBase()` during app bootstrap. */
export function apiUrl(path: string): string {
  const base = getBackendBase();
  if (base === null) {
    // Called before bootstrap — fall back to relative so dev keeps
    // working. In prod this path shouldn't be reached because
    // `main.tsx` awaits resolveBackendBase() before rendering.
    return path;
  }
  return `${base}${path}`;
}

/** Drop-in fetch replacement for same-origin API calls. */
export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), init);
}

/** Drop-in EventSource replacement. */
export function apiEventSource(path: string): EventSource {
  return new EventSource(apiUrl(path));
}

/** Ensure the base URL is resolved. Call once in `main.tsx` before render. */
export async function bootstrapApi(): Promise<void> {
  await resolveBackendBase();
}
