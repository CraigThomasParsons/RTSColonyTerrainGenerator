# CivicOverreach — Phase Plan

## Phase 1 (Current)

Implementation:
- Rule-based
- Heightmap-only
- SimCity-inspired heuristics
- Synthetic disasters

No external engines.
No simulation loops.

Purpose:
- Establish ruins as concrete geometry.
- Prove gameplay value.
- Keep pipeline simple.

---

## Phase 2 (Reserved)

Implementation:
- Headless simulation
- AI-controlled play
- Instrumentation and probes
- Disposable simulation runs

Pipeline model:

input artifacts
   ↓
headless simulation (AI plays)
   ↓
instrumentation / probes
   ↓
worldpayload (JSON)

Phase 2 MUST:
- Preserve output schema exactly.
- Replace internals only.

---

## Phase 3 (Optional / Future)

- Multi-era collapse
- Partial rebuilding
- Pre-player factions
- Climate-linked disasters

No phase may break downstream consumers.
