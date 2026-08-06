import type { GenerateWorldRequest, JobAccepted } from "./contract.ts";
import { parseJsonWithInt64, stringifyJsonWithInt64 } from "./int64.ts";

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
}

export function createMapGenClient({
  baseUrl,
  fetch: fetchImpl = globalThis.fetch,
}: MapGenClientOptions): MapGenClient {
  const send = async <T>(path: string, init: RequestInit): Promise<T> => {
    const response = await fetchImpl(`${baseUrl}${path}`, init);
    return parseJsonWithInt64<T>(await response.text());
  };

  return {
    submitWorld: (request) =>
      send<JobAccepted>("/worlds", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: stringifyJsonWithInt64(request),
      }),
  };
}
