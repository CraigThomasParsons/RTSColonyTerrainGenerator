import { useCallback, useEffect, useMemo, useSyncExternalStore } from "react";

import type { GenerateWorldRequest } from "~/shared/api/contract.ts";
import type { MapGenClient } from "~/shared/api/mapgenClient.ts";
import { createWorldJobTracker, type WorldJobSnapshot } from "./worldJobTracker.ts";

/**
 * React binding for the world-job tracker, and nothing more: the rules about polling live in
 * the tracker, which is why they are tested without a renderer. This hook exists so a
 * component can read snapshots and so an unmount stops the polling.
 */

export const IDLE_SNAPSHOT: WorldJobSnapshot = {
  phase: "idle",
  jobId: null,
  status: null,
  preview: null,
  error: null,
};

export interface UseWorldJobResult {
  snapshot: WorldJobSnapshot;
  generate: (request: GenerateWorldRequest) => void;
}

export function useWorldJob(client: MapGenClient, pollIntervalMs: number): UseWorldJobResult {
  const tracker = useMemo(
    () => createWorldJobTracker({ client, pollIntervalMs }),
    [client, pollIntervalMs],
  );

  // An unmounted page must not keep asking the API how a job it no longer shows is doing.
  useEffect(() => () => tracker.stop(), [tracker]);

  const snapshot = useSyncExternalStore(tracker.subscribe, tracker.getSnapshot);

  const generate = useCallback(
    (request: GenerateWorldRequest) => {
      void tracker.start(request);
    },
    [tracker],
  );

  return { snapshot, generate };
}
