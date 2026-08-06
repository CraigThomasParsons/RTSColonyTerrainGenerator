/**
 * The TypeScript mirror of the Wire Contract in `docs/plans/map-gui-prototype.md`.
 *
 * Hand-written on purpose (ADR 0006's codegen question stays open; this slice is too small
 * to justify a codegen step) and concentrated in this one module so the later swap to a
 * generated type — or to a Laravel BFF (Backend For Frontend) transport — is cheap. Phase 2 asserts the raw JSON
 * server-side, so a renamed field fails there rather than hiding here.
 *
 * Field names are snake_case because the wire is snake_case: AMPB consumes the map document
 * verbatim and one convention across the surface beats a mixed one. No camelCase mapping
 * layer is introduced — it would be a second vocabulary with nothing to say.
 *
 * `seed` is the one deliberate departure from a literal mirror. It is an `int64` on the
 * wire, which exceeds `Number.MAX_SAFE_INTEGER`, so it is carried as a decimal string in
 * TypeScript and written unquoted onto the wire. See `int64.ts`.
 */

/** A signed 64-bit integer, held losslessly as a decimal string. */
export type Int64String = string;

// ── POST /worlds ────────────────────────────────────────────────────────────────────

export interface GenerateWorldRequest {
  /** Omitted means the server picks one and echoes it back (ADR 0004 §4). */
  seed?: Int64String;
  map_width_in_cells: number;
  map_height_in_cells: number;
  /** Human label. The slug is derived server-side. */
  name?: string;
}

export interface JobAccepted {
  job_id: string;
  status: JobStatusValue;
  seed: Int64String;
  submitted_at_utc: string;
}

// ── GET /worlds/{job_id} ────────────────────────────────────────────────────────────

/** Lowercase strings on the wire, never enum ordinals: an ordinal is not a contract. */
export const JOB_STATUSES = ["queued", "running", "succeeded", "failed", "cancelled"] as const;

export type JobStatusValue = (typeof JOB_STATUSES)[number];

const TERMINAL_STATUSES: ReadonlySet<string> = new Set([
  "succeeded",
  "failed",
  "cancelled",
]);

/** The states after which the client stops polling. */
export const isTerminalStatus = (status: string): boolean => TERMINAL_STATUSES.has(status);

export interface JobStatus {
  job_id: string;
  status: JobStatusValue;
  /**
   * A stage name from `MapGenerator/stages.md`, or null while queued. Treated as an opaque
   * display string: the client must not branch on it, because the stage list is
   * legacy-pipeline vocabulary that changes as the .NET conversion proceeds.
   */
  stage: string | null;
  /** 0–100, monotonically non-decreasing within a job. Advisory only. */
  pct: number;
  seed: Int64String;
  map_width_in_cells: number;
  map_height_in_cells: number;
  submitted_at_utc: string;
  completed_at_utc: string | null;
  /** Non-null iff `status` is `failed`; human-readable by construction. */
  error: string | null;
}

// ── GET /worlds/{job_id}/map-document ───────────────────────────────────────────────

/** Row/col, never x/y: AMPB's documents are row/col throughout (ADR 0004 §2). */
export interface GridPosition {
  row: number;
  col: number;
}

export interface OrcBuilding extends GridPosition {
  type: string;
  tile_size: number;
}

export interface NamedStructure extends GridPosition {
  name: string;
  tile_size: number;
}

/** The document shape this client understands. Anything else is refused loudly. */
export const MAP_DOCUMENT_VERSION = 1;

export interface MapDocument {
  version: number;
  job_id: string;
  seed: Int64String;
  generator_version: string;

  slug: string;
  name: string;
  description: string;
  thumbnail_color: string;

  human_town_hall: GridPosition;
  /** Collections are always present and possibly empty — never omitted, never null. */
  human_workers: GridPosition[];
  orc_buildings: OrcBuilding[];
  mines: NamedStructure[];
  trees: GridPosition[];
  stones: GridPosition[];
  roads: GridPosition[];
}

// ── GET /worlds/{job_id}/preview ────────────────────────────────────────────────────

/** Tile x/y, matching `.playable.json`. The preview is the one document that speaks x/y. */
export interface PreviewStartZone {
  id: string;
  x: number;
  y: number;
}

export interface PreviewResourceCluster {
  id: string;
  type: string;
  x: number;
  y: number;
  start_id: string;
}

export const MAP_PREVIEW_VERSION = 1;

export interface MapPreview {
  version: number;
  job_id: string;
  width: number;
  height: number;
  terrain_palette: string[];
  /** Row-major (`index = y * width + x`), length `width * height`, indices into the palette. */
  terrain: number[];
  start_zones: PreviewStartZone[];
  resource_clusters: PreviewResourceCluster[];
}

// ── Errors ──────────────────────────────────────────────────────────────────────────

/** RFC 7807 `application/problem+json`; every non-2xx response carries one. */
export interface ProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  /** Mapped straight to the UI — the server's error strings are already human-readable. */
  detail?: string;
  instance?: string;
}
