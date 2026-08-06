import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { JobStatus, MapPreview } from "~/shared/api/contract.ts";
import type { MapGenClient } from "~/shared/api/mapgenClient.ts";
import { MapStudioPage } from "./MapStudioPage.tsx";

/**
 * The whole slice, in one test: a person submits a job, the page narrates the stages while
 * the server works, and the map appears when it is done. The client is faked at the module
 * boundary — the HTTP bytes have their own tests — so what this asserts is the asynchronous
 * shape: 202 first, a map only after `succeeded`.
 */
const JOB_ID = "43860dcf-6469-42a7-9843-4e33abeacfac";
const POLL_INTERVAL_MS = 1000;

const statusOf = (overrides: Partial<JobStatus>): JobStatus => ({
  job_id: JOB_ID,
  status: "running",
  stage: "Heightmap",
  pct: 10,
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
  width: 4,
  height: 4,
  terrain_palette: ["water", "grass"],
  terrain: [0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0],
  start_zones: [{ id: "start_1", x: 1, y: 1 }],
  resource_clusters: [{ id: "start_1_wood", type: "wood", x: 2, y: 2, start_id: "start_1" }],
};

beforeEach(() => {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  }));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("MapStudioPage", () => {
  it("submits a job, narrates its stages, and renders the map once it succeeds", async () => {
    const user = userEvent.setup();

    const getJobStatus = vi
      .fn()
      .mockResolvedValueOnce(statusOf({ status: "queued", stage: null, pct: 0 }))
      .mockResolvedValueOnce(statusOf({ status: "running", stage: "Tiler", pct: 55 }))
      .mockResolvedValue(
        statusOf({ status: "succeeded", stage: "AgileMedievalExport", pct: 100 }),
      );

    const client = {
      submitWorld: vi.fn().mockResolvedValue({
        job_id: JOB_ID,
        status: "queued",
        seed: "1234567890",
        submitted_at_utc: "2026-01-28T00:42:24Z",
      }),
      getJobStatus,
      getMapPreview: vi.fn().mockResolvedValue(PREVIEW),
      getMapDocument: vi.fn(),
    } as unknown as MapGenClient;

    render(<MapStudioPage client={client} pollIntervalMs={POLL_INTERVAL_MS} />);

    expect(screen.getByText(/no map yet/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /generate/i }));

    // The submit returned 202, not a map.
    await waitFor(() => expect(screen.getByText("queued")).toBeInTheDocument());
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(client.getMapPreview).not.toHaveBeenCalled();

    await waitFor(() => expect(screen.getByText("Tiler")).toBeInTheDocument(), {
      timeout: 4000,
    });

    const canvas = await screen.findByRole("img", { name: /4 x 4/i }, { timeout: 4000 });
    expect(canvas).toBeInTheDocument();
    expect(client.getMapPreview).toHaveBeenCalledWith(JOB_ID);
    expect(screen.getByRole("button", { name: /^generate$/i })).toBeEnabled();
  });

  it("shows the failure and no map when the job fails", async () => {
    const user = userEvent.setup();

    const client = {
      submitWorld: vi.fn().mockResolvedValue({
        job_id: JOB_ID,
        status: "queued",
        seed: "1234567890",
        submitted_at_utc: "2026-01-28T00:42:24Z",
      }),
      getJobStatus: vi.fn().mockResolvedValue(
        statusOf({ status: "failed", error: "Tiler stage rejected the heightmap." }),
      ),
      getMapPreview: vi.fn(),
      getMapDocument: vi.fn(),
    } as unknown as MapGenClient;

    render(<MapStudioPage client={client} pollIntervalMs={POLL_INTERVAL_MS} />);
    await user.click(screen.getByRole("button", { name: /generate/i }));

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Tiler stage rejected the heightmap.",
      ),
    );
    expect(screen.getByText(/no map yet/i)).toBeInTheDocument();
    expect(client.getMapPreview).not.toHaveBeenCalled();
  });
});
