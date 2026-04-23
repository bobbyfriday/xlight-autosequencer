/**
 * T031 — verify backend base URL resolution via Tauri event + fallback
 * to the get_backend_port command for late listeners.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the Tauri API modules BEFORE importing the module under test.
let eventHandlers: Record<string, ((e: { payload: unknown }) => void)[]> = {};
let pendingInvokePort: number | null = null;

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async (event: string, handler: (e: { payload: unknown }) => void) => {
    eventHandlers[event] = eventHandlers[event] ?? [];
    eventHandlers[event].push(handler);
    return () => {
      eventHandlers[event] = (eventHandlers[event] ?? []).filter((h) => h !== handler);
    };
  }),
}));

vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn(async (cmd: string) => {
    if (cmd === "get_backend_port") return pendingInvokePort;
    throw new Error(`unexpected invoke: ${cmd}`);
  }),
}));

async function loadFresh() {
  vi.resetModules();
  const mod = await import("./backendPort");
  mod.__resetBackendBaseForTests();
  return mod;
}

function emit(event: string, payload: unknown) {
  for (const h of eventHandlers[event] ?? []) h({ payload });
}

beforeEach(() => {
  eventHandlers = {};
  pendingInvokePort = null;
  // Pretend we're in a production Tauri window, not in Vite dev.
  vi.stubGlobal("import", { meta: { env: { DEV: false } } });
  vi.stubGlobal("window", { __TAURI_INTERNALS__: {} } as any);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("resolveBackendBase", () => {
  it("returns empty string in dev mode", async () => {
    vi.stubGlobal("import", { meta: { env: { DEV: true } } });
    const mod = await loadFresh();
    await expect(mod.resolveBackendBase()).resolves.toBe("");
  });

  it("resolves via the backend-ready event", async () => {
    const mod = await loadFresh();
    const promise = mod.resolveBackendBase();
    // Simulate Rust emitting the event after the listener attached.
    setTimeout(() => emit("backend-ready", { port: 54321 }), 0);
    await expect(promise).resolves.toBe("http://127.0.0.1:54321");
  });

  it("falls back to get_backend_port when event already fired", async () => {
    pendingInvokePort = 61234;
    const mod = await loadFresh();
    await expect(mod.resolveBackendBase()).resolves.toBe("http://127.0.0.1:61234");
  });

  it("caches the resolved base for subsequent calls", async () => {
    const mod = await loadFresh();
    setTimeout(() => emit("backend-ready", { port: 55555 }), 0);
    const first = await mod.resolveBackendBase();
    const second = await mod.resolveBackendBase();
    expect(first).toBe(second);
    expect(mod.getBackendBase()).toBe("http://127.0.0.1:55555");
  });
});
