# Tasks: 01-cell-to-tile

<!-- Lifecycle steps 7 and 8: implementation and tests, as thin ordered slices. -->

Implementation slices in execution order for issue #7 (milestone M3), branch
`feature/7-m3-epic-1-verified-celltotile-expansion`. Each task names its outputs and
the command that proves it. Update this file as tasks complete or as reality corrects
the plan (same change as the code).

Baseline evidence (standard step 1) already exists from Phase 0: the golden-job
fixtures under `tests/fixtures/golden/` and the hash harness in
`tests/MapGen.CompatibilityTests`. No new fixture capture is needed for this slice.

## Task 1 — Update the feature file to the charter's four scenarios

- **What:** Replace the current two-scenario `@wip` draft with the charter's four
  scenarios (origin cell, interior cell `3,4`, final valid cell `9,9`, out-of-bounds
  rejection `10,9`), keeping tag `@slice-01-cell-to-tile`, tagging the rejection
  scenario `@net-only`, and dropping `@wip` once steps exist (Task 2).
- **Outputs:** `tests/bdd/features/01-cell-to-tile/cell-to-tile-expansion.feature`.
- **Validation:** `npm run bdd:smoke` — the feature parses and the suite still
  passes.
- **Status:** todo.

## Task 2 — Step definitions and the legacy profile adapter

- **What:** Implement the Gherkin steps against a profile-selected adapter. The
  `legacy` adapter synthesizes a 10×10 `.heightmap` with a distinctive terrain value
  at only the target cell, runs `MapGenerator/Tiler/bin/published/Tiler <heightmap>`
  from a per-scenario scratch directory (the binary writes `./outbox/<id>.maptiles`
  relative to CWD), parses the `.maptiles`, and asserts exactly four tiles carry
  that terrain byte at exactly the four expected coordinates.
- **Outputs:** step definitions and adapter under `tests/bdd/steps/` and
  `tests/bdd/support/`.
- **Validation:** `just bdd-legacy` — scenarios 1–3 green on the `legacy` profile
  (`@net-only` excluded by the profile).
- **Status:** todo.

## Task 3 — Verified Model

- **What:** The Level B verified reference: `ExpandCell` plus lemmas for
  exactly-four, uniqueness, in-bounds, exact corner coordinates, and doubled
  dimensions. Determinism is structural (pure function).
- **Outputs:** `specs/tiling/CellToTile.dfy`.
- **Validation:** `just verify` (equivalently
  `dafny verify specs/tiling/CellToTile.dfy`) — all obligations discharged.
- **Status:** done (file authored; verification runs in the gate ladder).

## Task 4 — Verification report

- **What:** `verification-report.md` recording what was proved, what was assumed,
  and what remains unverified. Written by the human reviewer after the verification
  run — not authored alongside this spec pack.
- **Outputs:** `docs/specs/01-cell-to-tile/verification-report.md`.
- **Validation:** file present and honest; reviewed in the closing PR.
- **Status:** todo (human-authored).

## Task 5 — Domain value objects and CellExpander

- **What:** Implement `CellCoordinate`, `CellMapDimensions`, `TileCoordinate`,
  `TileMapDimensions`, and `TileRegion` with their invariants and typed failures,
  plus the `CellExpander` domain service encoding the contract in
  `requirements.md`.
- **Outputs:** `src/MapGen.Domain` (Tile Resolution namespace).
- **Validation:** `just build` compiles; covered by Task 6 tests.
- **Status:** todo.

## Task 6 — Unit and property tests

- **What:** Unit examples from the charter's test plan (origin, interior, final
  valid cell; negative coordinate; coordinate equal to width/height; zero and
  negative dimensions) and FsCheck properties mirroring the Dafny lemmas (count is
  four, distinct, in bounds, extrema `2x`/`2x+1`/`2y`/`2y+1`, repeat call returns an
  identical result).
- **Outputs:** `tests/MapGen.Domain.Tests`.
- **Validation:** `just test-unit` — green.
- **Status:** todo.

## Task 7 — Command and handler

- **What:** `ResolveTileRegionCommand` and its handler in `MapGen.Application`:
  validate, call `CellExpander`, return the `TileRegion` or a typed failure. No
  persistence, no query.
- **Outputs:** `src/MapGen.Application`; handler tests in
  `tests/MapGen.Domain.Tests`.
- **Validation:** `just test-unit` — handler tests green, including the rejection
  path.
- **Status:** todo.

## Task 8 — Architecture rules for the new surface

- **What:** Extend `MapGen.ArchitectureTests` so dependency purity covers the
  slice's projects: Domain depends on nothing infrastructural; Application depends
  only on Domain (and Contracts); the new Cli (Task 9) depends inward only.
- **Outputs:** `tests/MapGen.ArchitectureTests`.
- **Validation:** `just test-architecture` — green.
- **Status:** todo.

## Task 9 — MapGen.Cli `expand-cell` entry point

- **What:** A minimal CLI project exposing the command as `expand-cell` for the BDD
  `net` profile: parse arguments, dispatch the command, print the region or the
  typed failure. Add the project to `MapGen.slnx`.
- **Outputs:** `src/MapGen.Cli`; updated `MapGen.slnx`.
- **Validation:** `dotnet run --project src/MapGen.Cli -- expand-cell` with the
  charter's examples prints the expected region; rejection input exits non-zero
  with the failure named.
- **Status:** todo.

## Task 10 — Compatibility evidence in MapGen.CompatibilityTests

- **What:** Assert dimension doubling against the golden jobs: each 64×64-cell
  golden job's `.maptiles` header declares 128×128 tiles. (Per-cell expansion
  evidence against the real legacy binary is Task 2's adapter; see `acceptance.md`
  for the full evidence strategy.)
- **Outputs:** `tests/MapGen.CompatibilityTests`.
- **Validation:** `just test-compatibility` — green.
- **Status:** todo.

## Task 11 — Same Gherkin green on the net profile

- **What:** Wire the `net` profile adapter to `MapGen.Cli expand-cell` so all four
  scenarios (including `@net-only` rejection) pass from the same feature file.
- **Outputs:** `net` adapter under `tests/bdd/support/`.
- **Validation:** `just bdd-net` — all four scenarios green.
- **Status:** todo.

## Task 12 — Full gate ladder and promotion

- **What:** Run the whole quality surface, then promote: append
  `@slice-01-cell-to-tile` to `specs/dafny-ready.tags` and
  `tests/bdd/net-ready.tags` in this PR, with the charter exit criteria met
  (see `acceptance.md`).
- **Outputs:** updated promotion ledgers; PR evidence per `acceptance.md`.
- **Validation:** `just quality` — every gate green (format, build, verify, unit,
  architecture, compatibility, BDD smoke + legacy) plus `just bdd-net`.
- **Status:** todo.
