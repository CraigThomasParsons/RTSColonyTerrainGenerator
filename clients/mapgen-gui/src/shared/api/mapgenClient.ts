import type {
  GenerateWorldRequest,
  JobAccepted,
  JobStatus,
  MapDocument,
  MapPreview,
  ProblemDetails,
} from "./contract.ts";
import { MAP_DOCUMENT_VERSION, MAP_PREVIEW_VERSION } from "./contract.ts";
import { parseJsonWithInt64, stringifyJsonWithInt64 } from "./int64.ts";

/**
 * A non-2xx response. The server answers RFC 7807 `application/problem+json` on every
 * failure and its `detail` strings are human-readable by construction (they are the
 * `Result<T>.Error` values from the application layer), so the message is the detail
 * verbatim — the client adds no second vocabulary of its own.
 */
export class MapGenApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetails | undefined;

  constructor(status: number, message: string, problem?: ProblemDetails) {
    super(message);
    this.name = "MapGenApiError";
    this.status = status;
    this.problem = problem;
  }

  /** Unknown job. */
  get isNotFound(): boolean {
    return this.status === 404;
  }

  /** Collected before the job succeeded — keep waiting, this is not a dead end. */
  get isNotReady(): boolean {
    return this.status === 409;
  }
}

export interface MapGenClientOptions {
  /** Defaults to `VITE_MAPGEN_API_URL`; the API binds loopback only. */
  baseUrl: string;
  /** Injected so tests drive the HTTP seam without a server. */
  fetch?: typeof fetch;
}

/**
 * The only place this client speaks HTTP. Everything above it (entities, features) works in
 * contract types, so Phase 2's swap to a Laravel BFF transport replaces this module alone.
 */
export interface MapGenClient {
  submitWorld(request: GenerateWorldRequest): Promise<JobAccepted>;
  getJobStatus(jobId: string): Promise<JobStatus>;
  getMapDocument(jobId: string): Promise<MapDocument>;
  getMapPreview(jobId: string): Promise<MapPreview>;
}

export function createMapGenClient({
  baseUrl,
  fetch: fetchImpl = globalThis.fetch,
}: MapGenClientOptions): MapGenClient {
  const send = async <T>(path: string, init?: RequestInit): Promise<T> => {
    const response = await fetchImpl(`${baseUrl}${path}`, init ?? {});
    const text = await response.text();

    if (!response.ok) {
      throw toApiError(response.status, text);
    }

    return parseJsonWithInt64<T>(text);
  };

  return {
    submitWorld: (request) =>
      send<JobAccepted>("/worlds", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: stringifyJsonWithInt64(request),
      }),

    getJobStatus: (jobId) => send<JobStatus>(`/worlds/${encodeURIComponent(jobId)}`),

    getMapDocument: async (jobId) =>
      assertVersion(
        "map document",
        MAP_DOCUMENT_VERSION,
        await send<MapDocument>(`/worlds/${encodeURIComponent(jobId)}/map-document`),
      ),

    getMapPreview: async (jobId) =>
      assertVersion(
        "map preview",
        MAP_PREVIEW_VERSION,
        await send<MapPreview>(`/worlds/${encodeURIComponent(jobId)}/preview`),
      ),
  };
}

/**
 * A document's `version` increments on any shape change, so an unexpected one means the
 * client is about to render a map it does not understand. Refuse it loudly rather than
 * parsing leniently and drawing something subtly wrong.
 */
function assertVersion<T extends { version: number }>(
  what: string,
  expected: number,
  document: T,
): T {
  if (document.version !== expected) {
    throw new MapGenContractError(
      `MapGen.Api returned a ${what} at version ${document.version}; ` +
        `this client understands version ${expected} only.`,
    );
  }
  return document;
}

/** The wire shape is not what this client was written against. */
export class MapGenContractError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "MapGenContractError";
  }
}

/** A failure body that is not problem+json is still a failure worth naming. */
function toApiError(status: number, body: string): MapGenApiError {
  try {
    const problem = JSON.parse(body) as ProblemDetails;
    if (problem && typeof problem === "object" && typeof problem.detail === "string") {
      return new MapGenApiError(status, problem.detail, problem);
    }
  } catch {
    // Fall through to the status-only message below.
  }

  return new MapGenApiError(status, `MapGen.Api responded ${status}.`);
}
