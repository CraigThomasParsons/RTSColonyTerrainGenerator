/**
 * Build-time client configuration. Both values are fixed by the Wire Contract; they are env
 * vars rather than constants so a different local port does not need a code change.
 */

/**
 * MapGen.Api binds loopback only and is never exposed (ADR 0004).
 *
 * The literal 127.0.0.1 rather than localhost, because Kestrel binds the IPv4 loopback
 * alone: localhost can resolve to [::1] first, where nothing is listening, and the request
 * is refused before CORS is ever reached.
 */
export const MAPGEN_API_URL: string =
  import.meta.env.VITE_MAPGEN_API_URL ?? "http://127.0.0.1:5187/api/v1";

/**
 * Phase 1 polls at a fixed interval. ADR 0006 resolves push-vs-poll for AMPB (Reverb/Echo);
 * the standalone prototype has no Reverb, so 1000 ms it is.
 */
export const POLL_INTERVAL_MS: number = Number(
  import.meta.env.VITE_MAPGEN_POLL_INTERVAL_MS ?? 1000,
);
