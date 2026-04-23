/**
 * T064 — verify nativeDialog dev/prod dispatch.
 *
 * Production path is covered by mocking the Tauri dialog plugin;
 * dev path falls through to an HTML file input.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock the dialog plugin BEFORE importing the SUT.
vi.mock("@tauri-apps/plugin-dialog", () => ({
  open: vi.fn(),
  save: vi.fn(),
}));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("nativeDialog — Tauri mode", () => {
  beforeEach(() => {
    vi.stubGlobal("window", { __TAURI_INTERNALS__: {} } as any);
  });

  it("openAudio returns absolute paths from Tauri dialog", async () => {
    const { open } = await import("@tauri-apps/plugin-dialog");
    (open as any).mockResolvedValue(["/Users/me/song.mp3"]);

    const { openAudio } = await import("./nativeDialog");
    const result = await openAudio({ multiple: false });

    expect(result.usable).toBe(true);
    expect(result.paths).toEqual(["/Users/me/song.mp3"]);
  });

  it("openAudio returns empty array when user cancels", async () => {
    const { open } = await import("@tauri-apps/plugin-dialog");
    (open as any).mockResolvedValue(null);

    vi.resetModules();
    const { openAudio } = await import("./nativeDialog");
    const result = await openAudio();

    expect(result.paths).toEqual([]);
    expect(result.usable).toBe(true);
  });

  it("saveSequence returns selected destination", async () => {
    const { save } = await import("@tauri-apps/plugin-dialog");
    (save as any).mockResolvedValue("/Users/me/out.xsq");

    vi.resetModules();
    const { saveSequence } = await import("./nativeDialog");
    expect(await saveSequence()).toBe("/Users/me/out.xsq");
  });

  it("saveSequence returns null when user cancels", async () => {
    const { save } = await import("@tauri-apps/plugin-dialog");
    (save as any).mockResolvedValue(null);

    vi.resetModules();
    const { saveSequence } = await import("./nativeDialog");
    expect(await saveSequence()).toBeNull();
  });
});

describe("nativeDialog — dev browser mode", () => {
  beforeEach(() => {
    // No __TAURI_INTERNALS__ — we're in a plain browser.
    vi.stubGlobal("window", {} as any);
  });

  it("saveSequence returns null in dev so callers fall back to browser download", async () => {
    vi.resetModules();
    const { saveSequence } = await import("./nativeDialog");
    expect(await saveSequence()).toBeNull();
  });
});
