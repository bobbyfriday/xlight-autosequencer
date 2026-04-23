/**
 * Zustand store tracking the in-progress demucs weights download.
 *
 * State machine:
 *   idle → prompting → downloading → complete
 *                                 → error (from any state)
 *
 * Subscribes to the backend SSE stream (/api/v1/models/<name>/download)
 * and updates per-shard + overall progress.
 */
import { create } from "zustand";
import { apiUrl } from "../lib/apiClient";

export type WeightsPhase = "idle" | "prompting" | "downloading" | "complete" | "error";

export interface ModelStatus {
  name: string;
  present: boolean;
  size_bytes: number;
  license: string;
  license_note: string;
  shard_count: number;
}

interface WeightsState {
  phase: WeightsPhase;
  modelName: string | null;
  status: ModelStatus | null;
  overallBytes: number;
  overallTotal: number;
  currentShardName: string | null;
  errorMessage: string | null;
  /** Close the SSE EventSource. */
  _closer: (() => void) | null;

  /** Fetch `/models/<name>/status` and move to `prompting`. */
  promptForDownload: (modelName: string) => Promise<void>;
  /** Start the actual download. User must have confirmed first. */
  startDownload: () => void;
  /** Dismiss (sets phase back to idle). */
  dismiss: () => void;
}

export const useWeightsDownloadStore = create<WeightsState>((set, get) => ({
  phase: "idle",
  modelName: null,
  status: null,
  overallBytes: 0,
  overallTotal: 0,
  currentShardName: null,
  errorMessage: null,
  _closer: null,

  async promptForDownload(modelName: string) {
    const r = await fetch(apiUrl(`/api/v1/models/${modelName}/status`));
    if (!r.ok) {
      set({
        phase: "error",
        errorMessage: `Could not check model status: HTTP ${r.status}`,
        modelName,
      });
      return;
    }
    const status = (await r.json()) as ModelStatus;
    if (status.present) {
      // Already downloaded — no-op.
      set({ phase: "idle", modelName, status });
      return;
    }
    set({
      phase: "prompting",
      modelName,
      status,
      overallBytes: 0,
      overallTotal: status.size_bytes,
      errorMessage: null,
    });
  },

  startDownload() {
    const { modelName, _closer } = get();
    if (!modelName) return;
    if (_closer) _closer();

    set({ phase: "downloading", overallBytes: 0 });

    const es = new EventSource(apiUrl(`/api/v1/models/${modelName}/download`));

    es.addEventListener("progress", (event) => {
      const data = JSON.parse((event as MessageEvent).data) as {
        shard_name: string;
        overall_bytes: number;
        overall_total: number;
      };
      set({
        currentShardName: data.shard_name,
        overallBytes: data.overall_bytes,
        overallTotal: data.overall_total,
      });
    });

    es.addEventListener("complete", () => {
      set({ phase: "complete" });
      es.close();
    });

    es.addEventListener("error", (event) => {
      const raw = (event as MessageEvent).data;
      let message = "Download failed";
      try {
        if (raw) message = JSON.parse(raw).message ?? message;
      } catch {
        // EventSource network-level errors arrive as Event objects
        // without data. Leave the generic message.
      }
      set({ phase: "error", errorMessage: message });
      es.close();
    });

    set({ _closer: () => es.close() });
  },

  dismiss() {
    const { _closer } = get();
    if (_closer) _closer();
    set({
      phase: "idle",
      modelName: null,
      status: null,
      overallBytes: 0,
      overallTotal: 0,
      currentShardName: null,
      errorMessage: null,
      _closer: null,
    });
  },
}));
