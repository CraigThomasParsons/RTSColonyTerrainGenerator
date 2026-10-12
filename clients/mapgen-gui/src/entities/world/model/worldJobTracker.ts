import type { GenerateWorldRequest, JobStatus, MapPreview } from "~/shared/api/contract.ts";
import { isTerminalStatus } from "~/shared/api/contract.ts";
import { MapGenApiError, type MapGenClient } from "~/shared/api/mapgenClient.ts";

/**
 * The one place in the client that knows generation is asynchronous.
 *
 * Phase 1 polls: the standalone prototype has no Reverb, so it asks
 * `GET /worlds/{job_id}` every `pollIntervalMs` until a terminal state. ADR 0006 resolves
 * push-vs-poll for AMPB (Reverb/Echo), and this module is the seam that swap goes through —
 * everything above it consumes `WorldJobSnapshot` and never learns how the snapshot arrived.
 *
 * Deliberately framework-free. React binding is `useWorldJob`, a thin subscriber; the rules
 * about when to poll, when to stop, and when to collect are testable without a renderer.
 */

export type WorldJobPhase =
  | "idle"
  | "submitting"
  | "polling"
  | "ready"
  | "failed"
  | "cancelled";

export interface WorldJobSnapshot {
  phase: WorldJobPhase;
  jobId: string | null;
  /** The most recent poll response; the stage/pct the UI narrates. */
  status: JobStatus | null;
  /** Non-null once collected — the payload the preview renderer draws. */
  preview: MapPreview | null;
  /** The server's own message, verbatim; the client invents no error vocabulary. */
  error: string | null;
}

export interface WorldJobTrackerOptions {
  client: MapGenClient;
  /** The Wire Contract fixes 1000 ms, as a client config value rather than a constant. */
  pollIntervalMs: number;
}

export interface WorldJobTracker {
  /** Submit, then poll to completion. Resolves once the first poll has been answered. */
  start(request: GenerateWorldRequest): Promise<void>;
  /** Stop polling. Safe to call at any time, including when idle. */
  stop(): void;
  subscribe(listener: (snapshot: WorldJobSnapshot) => void): () => void;
  getSnapshot(): WorldJobSnapshot;
}

const IDLE: WorldJobSnapshot = {
  phase: "idle",
  jobId: null,
  status: null,
  preview: null,
  error: null,
};

export function createWorldJobTracker({
  client,
  pollIntervalMs,
}: WorldJobTrackerOptions): WorldJobTracker {
  let snapshot: WorldJobSnapshot = IDLE;
  const listeners = new Set<(snapshot: WorldJobSnapshot) => void>();

  let timer: ReturnType<typeof setTimeout> | null = null;
  /** Bumped on every start/stop so a poll in flight from a previous run is ignored. */
  let generation = 0;

  const emit = (patch: Partial<WorldJobSnapshot>) => {
    snapshot = { ...snapshot, ...patch };
    for (const listener of listeners) {
      listener(snapshot);
    }
  };

  const clearTimer = () => {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const scheduleNextPoll = (jobId: string, runGeneration: number) => {
    clearTimer();
    timer = setTimeout(() => {
      void poll(jobId, runGeneration);
    }, pollIntervalMs);
  };

  const poll = async (jobId: string, runGeneration: number): Promise<void> => {
    if (runGeneration !== generation) {
      return;
    }

    let status: JobStatus;
    try {
      status = await client.getJobStatus(jobId);
    } catch (error) {
      finish("failed", { error: messageOf(error) });
      return;
    }

    if (runGeneration !== generation) {
      return;
    }

    emit({ status });

    if (!isTerminalStatus(status.status)) {
      scheduleNextPoll(jobId, runGeneration);
      return;
    }

    if (status.status === "failed") {
      finish("failed", { error: status.error ?? "The generation job failed." });
      return;
    }

    if (status.status === "cancelled") {
      finish("cancelled", {});
      return;
    }

    await collect(jobId, runGeneration);
  };

  const collect = async (jobId: string, runGeneration: number): Promise<void> => {
    try {
      const preview = await client.getMapPreview(jobId);
      if (runGeneration === generation) {
        finish("ready", { preview });
      }
    } catch (error) {
      if (runGeneration !== generation) {
        return;
      }
      // 409 means "not yet", not "broken": the status said succeeded but the payload is not
      // published. Keep waiting rather than surfacing a dead end.
      if (error instanceof MapGenApiError && error.isNotReady) {
        scheduleNextPoll(jobId, runGeneration);
        return;
      }
      finish("failed", { error: messageOf(error) });
    }
  };

  const finish = (phase: WorldJobPhase, patch: Partial<WorldJobSnapshot>) => {
    clearTimer();
    emit({ phase, ...patch });
  };

  return {
    async start(request) {
      generation += 1;
      const runGeneration = generation;
      clearTimer();
      snapshot = { ...IDLE, phase: "submitting" };
      emit({});

      let jobId: string;
      try {
        // 202: never the map. A client that awaits a map from the submit call is wrong.
        const accepted = await client.submitWorld(request);
        jobId = accepted.job_id;
      } catch (error) {
        if (runGeneration === generation) {
          finish("failed", { error: messageOf(error) });
        }
        return;
      }

      if (runGeneration !== generation) {
        return;
      }

      emit({ phase: "polling", jobId });
      await poll(jobId, runGeneration);
    },

    stop() {
      generation += 1;
      clearTimer();
    },

    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },

    getSnapshot: () => snapshot,
  };
}

const messageOf = (error: unknown): string =>
  error instanceof Error ? error.message : String(error);
