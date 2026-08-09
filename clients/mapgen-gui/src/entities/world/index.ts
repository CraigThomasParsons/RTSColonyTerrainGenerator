/**
 * Public API of the `world` entity slice. Feature and widget slices import from here and
 * never reach into `model/` — that indirection is what lets Phase 2 replace polling with an
 * Echo subscription behind an unchanged surface.
 */
export {
  createWorldJobTracker,
  type WorldJobPhase,
  type WorldJobSnapshot,
  type WorldJobTracker,
  type WorldJobTrackerOptions,
} from "./model/worldJobTracker.ts";

export { IDLE_SNAPSHOT, useWorldJob, type UseWorldJobResult } from "./model/useWorldJob.ts";
