# CivicOverreach — Architecture

## Pipeline Position

Heightmap
│
├─▶ Tiler
├─▶ Weather
├─▶ OldInfrastructure (OpenTTD)
└─▶ CivicOverreach

CivicOverreach consumes ONLY heightmap artifacts.

---

## Output Contract (Immutable)

CivicOverreach MUST produce:

<job_id>.civic_overreach.worldpayload

With the following top-level structure:

{
  "concrete": {...},
  "heuristics": {...},
  "provenance": {...}
}

This schema must remain stable across phases.

---

## Concrete Section (Canonical)

Concrete data represents real, immutable world geometry.

Includes:
- bridges (intact, damaged, or collapsed)
- roads (partial, broken, overgrown)
- buildings (abandoned)

Later stages may:
- repair
- reuse
- decorate

Later stages may NOT invent or delete these structures.

---

## Heuristics Section (Advisory)

Heuristics explain *why* structures exist or failed.

Examples:
- overreach zones
- disaster events
- maintenance failures

Heuristics may be ignored by gameplay stages.

---

## Provenance Section

Tracks:
- stage name
- version (v1, phase2, etc.)
- approach used
- confidence level
