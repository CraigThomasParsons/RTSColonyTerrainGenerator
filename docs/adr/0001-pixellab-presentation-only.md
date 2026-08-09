# ADR 0001: PixelLab output is presentation-only

- Status: Accepted for the #49 experiment
- Date: 2026-08-08
- Issues: #49, #50, #55

## Context

RTSColonyTerrainGenerator owns deterministic terrain, traversability, features,
starts, resources and export contracts. PixelLab can add visual richness, but a
generated raster cannot reliably preserve or explain every gameplay cell.

## Decision

PixelLab output is an optional presentation artifact. Authoritative map data
produces a deterministic `VisualBrief`, semantic control image, protected mask
and decoration mask. A later adapter may submit those artifacts to PixelLab and
cache the result with complete provenance.

Generated pixels never feed terrain classification, collision, pathfinding,
resource placement, start selection, map export or validation. WorldPreview
will render an accepted image only beneath overlays reconstructed from the
authoritative payload. Offline deterministic rendering remains the fallback.

Candidates require structural validation and explicit acceptance. A warning,
dimension override, missing manifest, hash mismatch or rejected validation
prevents promotion.

## Consequences

- Visual generation can be nondeterministic without making gameplay
  nondeterministic.
- The pipeline can disable PixelLab without losing functionality.
- Control artifacts and manifests add storage, tests and operational work.
- Whole-map stylization may be rejected if it moves important geometry. In
  that case #54 may select a Wang-tileset plus transparent-object approach.
- Declared map dimensions must match tile extents. Issue #55 owns the existing
  inconsistency; strict generation fails closed until it is resolved.
