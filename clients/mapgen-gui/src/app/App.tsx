import { useMemo } from "react";

import { MapStudioPage } from "~/pages/map-studio";
import { createMapGenClient } from "~/shared/api/mapgenClient.ts";
import { MAPGEN_API_URL, POLL_INTERVAL_MS } from "~/shared/config/env.ts";

/**
 * Composition root. The transport is built here and injected downward, which is the whole
 * reason every slice below takes a client rather than importing one: Phase 2 swaps this
 * single line for a Laravel BFF (Backend For Frontend) client and nothing else moves.
 */
export function App() {
  const client = useMemo(() => createMapGenClient({ baseUrl: MAPGEN_API_URL }), []);

  return <MapStudioPage client={client} pollIntervalMs={POLL_INTERVAL_MS} />;
}
