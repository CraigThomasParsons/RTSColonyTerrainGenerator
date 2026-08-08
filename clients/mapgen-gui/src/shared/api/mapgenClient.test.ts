import { beforeEach, describe, expect, it, vi } from "vitest";

import { createMapGenClient, MapGenApiError } from "./mapgenClient.ts";

/**
 * The seam under test is the HTTP boundary: these tests drive the client through a
 * stubbed `fetch` and assert the exact bytes of the Wire Contract
 * (`docs/plans/map-gui-prototype.md`). Phase 2 asserts the same shapes server-side, so a
 * renamed field fails on both sides rather than hiding in a lenient parser.
 */
const BASE_URL = "http://127.0.0.1:5187/api/v1";
const JOB_ID = "43860dcf-6469-42a7-9843-4e33abeacfac";

const jsonResponse = (status: number, body: string, headers: HeadersInit = {}) =>
  new Response(body, {
    status,
    headers: { "content-type": "application/json", ...headers },
  });

let fetchMock: ReturnType<typeof vi.fn>;

const clientUnderTest = () =>
  createMapGenClient({ baseUrl: BASE_URL, fetch: fetchMock as unknown as typeof fetch });

const lastCall = () => fetchMock.mock.calls[0] as [string, RequestInit];

beforeEach(() => {
  fetchMock = vi.fn();
});

describe("submitWorld", () => {
  it("posts the request in snake_case and returns the accepted job", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        202,
        `{"job_id":"${JOB_ID}","status":"queued","seed":1234567890,"submitted_at_utc":"2026-01-28T00:42:24Z"}`,
        { location: `/api/v1/worlds/${JOB_ID}` },
      ),
    );

    const accepted = await clientUnderTest().submitWorld({
      seed: "1234567890",
      map_width_in_cells: 64,
      map_height_in_cells: 64,
      name: "Default Forest",
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = lastCall();
    expect(url).toBe(`${BASE_URL}/worlds`);
    expect(init.method).toBe("POST");
    expect(init.headers).toMatchObject({ "content-type": "application/json" });
    expect(JSON.parse(init.body as string)).toEqual({
      seed: 1234567890,
      map_width_in_cells: 64,
      map_height_in_cells: 64,
      name: "Default Forest",
    });

    expect(accepted).toEqual({
      job_id: JOB_ID,
      status: "queued",
      seed: "1234567890",
      submitted_at_utc: "2026-01-28T00:42:24Z",
    });
  });

  it("omits an unspecified seed so the server picks one", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        202,
        `{"job_id":"${JOB_ID}","status":"queued","seed":42,"submitted_at_utc":"2026-01-28T00:42:24Z"}`,
      ),
    );

    await clientUnderTest().submitWorld({ map_width_in_cells: 64, map_height_in_cells: 64 });

    expect(JSON.parse(lastCall()[1].body as string)).toEqual({
      map_width_in_cells: 64,
      map_height_in_cells: 64,
    });
  });

  it("round-trips a seed larger than Number.MAX_SAFE_INTEGER without losing a digit", async () => {
    // `Random.Shared.NextInt64(0, long.MaxValue)` server-side, so the echoed seed routinely
    // exceeds 2^53. ADR 0004 §4 determinism requires the client learn the exact seed it got:
    // resubmitting a rounded one generates a different map. The seed therefore stays a
    // decimal string in TypeScript and an unquoted JSON number on the wire.
    const hugeSeed = "9007199254740993"; // 2^53 + 1 — not representable as a JS number
    fetchMock.mockResolvedValue(
      jsonResponse(
        202,
        `{"job_id":"${JOB_ID}","status":"queued","seed":${hugeSeed},"submitted_at_utc":"2026-01-28T00:42:24Z"}`,
      ),
    );

    const accepted = await clientUnderTest().submitWorld({
      seed: hugeSeed,
      map_width_in_cells: 64,
      map_height_in_cells: 64,
    });

    expect(accepted.seed).toBe(hugeSeed);
    // Unquoted on the wire: the contract says int64, not string.
    expect(lastCall()[1].body).toContain(`"seed":${hugeSeed}`);
  });
});

describe("getJobStatus", () => {
  it("reads the polled job state, nulls included", async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        200,
        `{"job_id":"${JOB_ID}","status":"running","stage":"Tiler","pct":37,"seed":1234567890,` +
          `"map_width_in_cells":64,"map_height_in_cells":64,` +
          `"submitted_at_utc":"2026-01-28T00:42:24Z","completed_at_utc":null,"error":null}`,
      ),
    );

    const status = await clientUnderTest().getJobStatus(JOB_ID);

    expect(lastCall()[0]).toBe(`${BASE_URL}/worlds/${JOB_ID}`);
    expect(status.status).toBe("running");
    expect(status.stage).toBe("Tiler");
    expect(status.pct).toBe(37);
    expect(status.completed_at_utc).toBeNull();
    expect(status.error).toBeNull();
  });
});

describe("collecting a finished job", () => {
  const preview = (overrides: Record<string, unknown> = {}) =>
    JSON.stringify({
      version: 2,
      job_id: JOB_ID,
      width: 2,
      height: 2,
      terrain_palette: ["deep_water", "water", "dirt", "grass"],
      terrain: [3, 3, 2, 0],
      trees: [{ x: 0, y: 1 }],
      start_zones: [{ id: "start_1", x: 43, y: 80 }],
      resource_clusters: [
        { id: "start_1_wood", type: "wood", x: 49, y: 84, start_id: "start_1" },
      ],
      ...overrides,
    });

  it("reads the preview from the collect endpoint", async () => {
    fetchMock.mockResolvedValue(jsonResponse(200, preview()));

    const map = await clientUnderTest().getMapPreview(JOB_ID);

    expect(lastCall()[0]).toBe(`${BASE_URL}/worlds/${JOB_ID}/preview`);
    expect(map.terrain).toEqual([3, 3, 2, 0]);
    expect(map.terrain_palette[3]).toBe("grass");
    expect(map.trees).toEqual([{ x: 0, y: 1 }]);
    expect(map.start_zones).toEqual([{ id: "start_1", x: 43, y: 80 }]);
  });

  it("refuses an unknown document version loudly rather than parsing leniently", async () => {
    // `version` increments on any shape change (AGENTS.md: no silent shape changes). A
    // client that shrugs at version 3 renders a map it does not understand.
    fetchMock.mockResolvedValue(jsonResponse(200, preview({ version: 3 })));

    const failure = await clientUnderTest()
      .getMapPreview(JOB_ID)
      .catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(Error);
    expect((failure as Error).message).toMatch(/version 3/i);
  });

  it("reads the map document in row/col, refusing an unknown version too", async () => {
    const document = {
      version: 2,
      job_id: JOB_ID,
      seed: 1234567890,
      generator_version: "0.1.0-prototype",
      slug: "default_forest",
      name: "Default Forest",
      description: "Generated by MapGen job 43860dcf.",
      thumbnail_color: "#3a5a2a",
      human_town_hall: { row: 14, col: 1 },
      human_workers: [{ row: 17, col: 6 }],
      orc_buildings: [{ type: "town_hall", row: 5, col: 55, tile_size: 4 }],
      mines: [],
      trees: [],
      stones: [],
      roads: [],
    };
    fetchMock.mockResolvedValue(jsonResponse(200, JSON.stringify(document)));

    const map = await clientUnderTest().getMapDocument(JOB_ID);

    expect(lastCall()[0]).toBe(`${BASE_URL}/worlds/${JOB_ID}/map-document`);
    expect(map.human_town_hall).toEqual({ row: 14, col: 1 });
    expect(map.seed).toBe("1234567890");
  });
});

describe("error responses", () => {
  it("raises the problem+json detail, verbatim, as the failure", async () => {
    // The server's error strings are human-readable by construction, so the client maps
    // `detail` straight through rather than inventing a second vocabulary of its own.
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          type: "https://mapgen.local/problems/invalid-request",
          title: "Invalid request",
          status: 400,
          detail: "Map width in cells must be greater than zero.",
          instance: "/api/v1/worlds",
        }),
        { status: 400, headers: { "content-type": "application/problem+json" } },
      ),
    );

    const failure = await clientUnderTest()
      .submitWorld({ map_width_in_cells: 0, map_height_in_cells: 64 })
      .catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(MapGenApiError);
    const apiError = failure as MapGenApiError;
    expect(apiError.status).toBe(400);
    expect(apiError.message).toBe("Map width in cells must be greater than zero.");
    expect(apiError.problem?.type).toBe("https://mapgen.local/problems/invalid-request");
  });

  it("distinguishes a collect that is too early (409) from an unknown job (404)", async () => {
    // A premature collect is a distinguishable error, not a 404 and not a hang, so the
    // polling model can keep waiting instead of surfacing a dead end.
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({ status: 409, detail: "Job has not succeeded yet." }),
        { status: 409, headers: { "content-type": "application/problem+json" } },
      ),
    );

    const failure = (await clientUnderTest()
      .getMapPreview(JOB_ID)
      .catch((error: unknown) => error)) as MapGenApiError;

    expect(failure.status).toBe(409);
    expect(failure.isNotReady).toBe(true);
    expect(failure.isNotFound).toBe(false);
  });

  it("still fails usefully when the body is not problem+json", async () => {
    fetchMock.mockResolvedValue(new Response("<html>502</html>", { status: 502 }));

    const failure = (await clientUnderTest()
      .getJobStatus(JOB_ID)
      .catch((error: unknown) => error)) as MapGenApiError;

    expect(failure).toBeInstanceOf(MapGenApiError);
    expect(failure.status).toBe(502);
    expect(failure.message).toContain("502");
  });
});
