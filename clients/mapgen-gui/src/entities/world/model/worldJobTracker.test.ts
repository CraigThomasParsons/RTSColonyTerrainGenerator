import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { JobStatus, MapPreview } from "~/shared/api/contract.ts";
import { MapGenApiError, type MapGenClient } from "~/shared/api/mapgenClient.ts";
import { createWorldJobTracker, type WorldJobSnapshot } from "./worldJobTracker.ts";

/**
 * The seam under test is the entity model's own API — `start` / `subscribe` / `stop` — not
 * the timer or the HTTP client underneath it. Polling lives here and nowhere else, so Phase
 * 2 can replace this one model with an Echo subscription without touching a feature slice;
 * these tests describe the contract that replacement must honour.
 */
const JOB_ID = "43860dcf-6469-42a7-9843-4e33abeacfac";
const POLL_INTERVAL_MS = 1000;

const statusOf = (overrides: Partial<JobStatus> = {}): JobStatus => ({
  job_id: JOB_ID,
  status: "running",
  stage: "Tiler",
  pct: 37,
  seed: "1234567890",
  map_width_in_cells: 64,
  map_height_in_cells: 64,
  submitted_at_utc: "2026-01-28T00:42:24Z",
  completed_at_utc: null,
  error: null,
  ...overrides,
});

const PREVIEW: MapPreview = {
  version: 1,
  job_id: JOB_ID,
  width: 2,
  height: 2,
  terrain_palette: ["deep_water", "water", "dirt", "grass"],
  terrain: [3, 3, 2, 0],
  start_zones: [],
  resource_clusters: [],
};

interface Harness {
  client: MapGenClient;
  submitWorld: ReturnType<typeof vi.fn>;
  getJobStatus: ReturnType<typeof vi.fn>;
  getMapPreview: ReturnType<typeof vi.fn>;
}

const harness = (): Harness => {
  const submitWorld = vi.fn().mockResolvedValue({
    job_id: JOB_ID,
    status: "queued",
    seed: "1234567890",
    submitted_at_utc: "2026-01-28T00:42:24Z",
  });
  const getJobStatus = vi.fn();
  const getMapPreview = vi.fn().mockResolvedValue(PREVIEW);
  const client = {
    submitWorld,
    getJobStatus,
    getMapPreview,
    getMapDocument: vi.fn(),
  } as unknown as MapGenClient;
  return { client, submitWorld, getJobStatus, getMapPreview };
};

const trackerFor = ({ client }: Harness) => {
  const seen: WorldJobSnapshot[] = [];
  const tracker = createWorldJobTracker({ client, pollIntervalMs: POLL_INTERVAL_MS });
  tracker.subscribe((snapshot) => seen.push(snapshot));
  return { tracker, seen };
};

/** Let queued microtasks settle, then fire the next poll interval. */
const advanceOnePoll = async () => {
  await vi.advanceTimersByTimeAsync(POLL_INTERVAL_MS);
};

beforeEach(() => {
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("createWorldJobTracker", () => {
  it("submits, then polls at the configured interval until the job succeeds", async () => {
    const bench = harness();
    bench.getJobStatus
      .mockResolvedValueOnce(statusOf({ status: "queued", stage: null, pct: 0 }))
      .mockResolvedValueOnce(statusOf({ status: "running", pct: 60 }))
      .mockResolvedValue(statusOf({ status: "succeeded", pct: 100, stage: "Playable" }));

    const { tracker, seen } = trackerFor(bench);
    await tracker.start({ map_width_in_cells: 64, map_height_in_cells: 64 });

    expect(bench.submitWorld).toHaveBeenCalledTimes(1);
    expect(bench.getJobStatus).toHaveBeenCalledTimes(1);

    await advanceOnePoll();
    expect(bench.getJobStatus).toHaveBeenCalledTimes(2);

    await advanceOnePoll();
    expect(bench.getJobStatus).toHaveBeenCalledTimes(3);

    // Terminal: polling stops, and no further call happens however long we wait.
    await advanceOnePoll();
    await advanceOnePoll();
    expect(bench.getJobStatus).toHaveBeenCalledTimes(3);

    const last = seen.at(-1) as WorldJobSnapshot;
    expect(last.phase).toBe("ready");
    expect(last.preview).toEqual(PREVIEW);
    expect(last.status?.pct).toBe(100);
  });

  it("collects the preview exactly once, after the job succeeded and never before", async () => {
    const bench = harness();
    bench.getJobStatus
      .mockResolvedValueOnce(statusOf({ status: "running" }))
      .mockResolvedValue(statusOf({ status: "succeeded", pct: 100 }));

    const { tracker } = trackerFor(bench);
    await tracker.start({ map_width_in_cells: 64, map_height_in_cells: 64 });

    expect(bench.getMapPreview).not.toHaveBeenCalled();

    await advanceOnePoll();
    expect(bench.getMapPreview).toHaveBeenCalledTimes(1);
    expect(bench.getMapPreview).toHaveBeenCalledWith(JOB_ID);
  });

  it("stops on a failed job and surfaces the server's own error text", async () => {
    const bench = harness();
    bench.getJobStatus.mockResolvedValue(
      statusOf({ status: "failed", error: "Tiler stage rejected the heightmap." }),
    );

    const { tracker, seen } = trackerFor(bench);
    await tracker.start({ map_width_in_cells: 64, map_height_in_cells: 64 });
    await advanceOnePoll();

    const last = seen.at(-1) as WorldJobSnapshot;
    expect(last.phase).toBe("failed");
    expect(last.error).toBe("Tiler stage rejected the heightmap.");
    expect(bench.getJobStatus).toHaveBeenCalledTimes(1);
    expect(bench.getMapPreview).not.toHaveBeenCalled();
  });

  it("stops on a cancelled job", async () => {
    const bench = harness();
    bench.getJobStatus.mockResolvedValue(statusOf({ status: "cancelled" }));

    const { tracker, seen } = trackerFor(bench);
    await tracker.start({ map_width_in_cells: 64, map_height_in_cells: 64 });
    await advanceOnePoll();

    expect(seen.at(-1)?.phase).toBe("cancelled");
    expect(bench.getJobStatus).toHaveBeenCalledTimes(1);
  });

  it("keeps polling when a collect turns out to be premature", async () => {
    // A 409 means "not yet", not "broken": the status said succeeded but the collect
    // disagreed, so the tracker waits rather than surfacing a dead end.
    const bench = harness();
    bench.getJobStatus.mockResolvedValue(statusOf({ status: "succeeded", pct: 100 }));
    bench.getMapPreview
      .mockRejectedValueOnce(new MapGenApiError(409, "Job has not succeeded yet."))
      .mockResolvedValue(PREVIEW);

    const { tracker, seen } = trackerFor(bench);
    await tracker.start({ map_width_in_cells: 64, map_height_in_cells: 64 });

    expect(seen.at(-1)?.phase).toBe("polling");

    await advanceOnePoll();
    expect(seen.at(-1)?.phase).toBe("ready");
    expect(seen.at(-1)?.preview).toEqual(PREVIEW);
  });

  it("stops polling once stopped", async () => {
    const bench = harness();
    bench.getJobStatus.mockResolvedValue(statusOf({ status: "running" }));

    const { tracker } = trackerFor(bench);
    await tracker.start({ map_width_in_cells: 64, map_height_in_cells: 64 });
    expect(bench.getJobStatus).toHaveBeenCalledTimes(1);

    tracker.stop();
    await advanceOnePoll();
    await advanceOnePoll();

    expect(bench.getJobStatus).toHaveBeenCalledTimes(1);
  });

  it("reports a rejected submit without starting to poll", async () => {
    const bench = harness();
    bench.submitWorld.mockRejectedValue(
      new MapGenApiError(400, "Map width in cells must be greater than zero."),
    );

    const { tracker, seen } = trackerFor(bench);
    await tracker.start({ map_width_in_cells: 0, map_height_in_cells: 64 });

    expect(seen.at(-1)?.phase).toBe("failed");
    expect(seen.at(-1)?.error).toBe("Map width in cells must be greater than zero.");
    expect(bench.getJobStatus).not.toHaveBeenCalled();
  });
});
