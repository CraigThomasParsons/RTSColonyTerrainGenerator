# CivicOverreach — Validation Strategy

## Purpose

Validation is used to detect implausible results,
not to generate or correct world data.

---

## Validation Engines

Examples:
- OpenSC2K (viewer)
- StarCraft (map sanity checking)
- Custom debug viewers

These engines:
- visualize output
- surface problems
- do not write back into the pipeline

---

## Validation Flow

worldpayload
  ↓
engine-specific adapter
  ↓
visual inspection (AI or human)
  ↓
heuristic tuning (manual)

---

## Failure Is Acceptable

If validation shows issues:
- adjust CivicOverreach logic
- regenerate worldpayload
- never patch data inside the engine

Worldpayload remains the single source of truth.
