import { beforeEach, describe, expect, it, vi } from "vitest";

import { createMapGenClient } from "./mapgenClient.ts";

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
