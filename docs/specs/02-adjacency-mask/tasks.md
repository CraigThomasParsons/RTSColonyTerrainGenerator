# Tasks: 02-adjacency-mask

<!-- Lifecycle steps 7 and 8: implementation and tests, as thin ordered slices. -->

Implementation slices in execution order for issue #10 (milestone M4), branch
`feature/10-m4-epic-2-verified-adjacencymask-construction`. Each task names its outputs
and the command that proves it. Update this file as tasks complete or as reality
corrects the plan (same change as the code).

Baseline evidence (standard step 1) already exists from Phase 0: the golden-job
fixtures under `tests/fixtures/golden/` and the harness in
`tests/MapGen.CompatibilityTests`. No new fixture capture is needed for this slice —
the golden `.heightmap`/`.maptiles` pairs already carry the legacy masks in their
tile-id low nibbles.

## Task 1 — Author the feature file

- **What:** Write the slice's scenarios (interior cell → 15, origin corner → 6,
  differing-terrain neighbours → 0, adjacent-cell symmetry, out-of-bounds rejection),
  tagged `@slice-02-adjacency-mask`, with the rejection scenario tagged `@net-only`.
  Legacy-profile grids use terrain values in `[0, 3]`.
- **Outputs:** `tests/bdd/features/02-adjacency-mask/adjacency-mask.feature`.
- **Validation:** `npm run bdd:smoke` — the feature parses and the suite still passes.
- **Status:** todo.

## Task 2 — Step definitions and the legacy profile adapter

- **What:** Implement the Gherkin steps against a profile-selected adapter. The
  `legacy` adapter synthesizes a small `.heightmap` with the scenario's terrain layout
  (values `0..3`), runs `MapGenerator/Tiler/bin/published/Tiler <heightmap>` from a
  per-scenario scratch directory (the binary writes `./outbox/<id>.maptiles` relative
  to CWD), and reads the target cell's mask as the low nibble (`id & 0x0F`) of any one
  of its four 2×2 tiles.
- **Outputs:** step definitions and adapter under `tests/bdd/steps/` and
  `tests/bdd/support/` (reusing Epic 1's scratch-dir and binary-invocation helpers).
- **Validation:** `just bdd-legacy` — scenarios 1–4 green on the `legacy` profile
  (`@net-only` excluded by the profile).
- **Status:** todo.

## Task 3 — Verified Model

- **What:** The Level B verified reference: `Grid`, the four guarded bit functions,
  their sum `Mask`, and lemmas `MaskInRange`, `EdgeCellsNeverSetOffMapBits`,
  `EastWestSymmetry`, `NorthSouthSymmetry`, `BitsReflectNeighbourPredicate`.
  Determinism is structural (pure function).
- **Outputs:** `specs/tiling/AdjacencyMask.dfy`.
- **Validation:** `just verify` (equivalently
  `dafny verify specs/tiling/AdjacencyMask.dfy`) — all obligations discharged.
- **Status:** done (file authored and verifying: 15 obligations, 0 errors).

## Task 4 — Verification report

- **What:** `verification-report.md` recording what was proved (mask range, edge bits,
  both symmetry lemmas, bits-reflect-predicate), what was assumed, and what remains
  unverified — including that determinism carries no lemma because Dafny functions are
  pure. Written by the human reviewer after the verification run, not authored
  alongside this spec pack.
- **Outputs:** `docs/specs/02-adjacency-mask/verification-report.md`.
- **Validation:** file present and honest; reviewed in the closing PR.
- **Status:** todo (human-authored).

## Task 5 — Domain value objects and AdjacencyMaskCalculator

- **What:** Implement `TerrainGrid` (width, height, `terrain[x, y]`; rejects
  non-positive dimensions) and `AdjacencyMask` (byte `0..15` with named N/E/S/W
  accessors; rejects values above 15), plus the `AdjacencyMaskCalculator` domain
  service with `ComputeMask(grid, x, y)` and the row-major `ComputeMasks(grid)`,
  encoding the contract in `requirements.md`.
- **Outputs:** `src/MapGen.Domain` (Tile Resolution namespace).
- **Validation:** `just build` compiles; covered by Task 6 tests.
- **Status:** todo.

## Task 6 — Unit and property tests

- **What:** Unit examples from the slice's test plan (interior cell → 15, corner
  `(0,0)` → at most 6, all-different neighbours → 0, single-axis edges) and FsCheck
  properties mirroring the Dafny lemmas (mask in `[0, 15]`; each bit reflects its
  neighbour predicate; edge cells never set off-map bits; East⇔West and South⇔North
  symmetry across generated grids; repeat call returns an identical mask).
- **Outputs:** `tests/MapGen.Domain.Tests`.
- **Validation:** `just test-unit` — green.
- **Status:** todo.

## Task 7 — Command and handler (Mediator)

- **What:** `ComputeAdjacencyMaskCommand : IRequest<Result<AdjacencyMask>>` and its
  `IRequestHandler<,>` in `MapGen.Application`: validate, call
  `AdjacencyMaskCalculator.ComputeMask`, return the `AdjacencyMask` or a typed
  `Result` failure. Register it via the existing `AddMapGenApplication()` root (ADR
  0005). No persistence, no query.
- **Outputs:** `src/MapGen.Application`; handler and wiring tests in
  `tests/MapGen.Domain.Tests` / `MapGen.Application.Tests`.
- **Validation:** `just test-unit` — handler tests green, including the rejection path
  surfacing as a `Result` failure (not an exception).
- **Status:** todo.

## Task 8 — Architecture rules for the new surface

- **What:** Confirm `MapGen.ArchitectureTests` covers the slice: Domain depends on
  nothing infrastructural; Application depends only on Domain (and Contracts); the new
  Cli subcommand depends inward only; and the new `*Handler` implements
  `IRequestHandler<,>` (`Request_handlers_implement_the_mediator_handler_interface`).
- **Outputs:** `tests/MapGen.ArchitectureTests`.
- **Validation:** `just test-architecture` — green.
- **Status:** todo.

## Task 9 — MapGen.Cli `mask-cell` entry point

- **What:** Add the `mask-cell --width --height --x --y --terrain <csv>` subcommand for
  the BDD `net` profile: parse arguments, build the `TerrainGrid` from the row-major
  CSV, resolve `ISender`, send the command, and print the mask or the typed failure.
- **Outputs:** `src/MapGen.Cli`.
- **Validation:** `dotnet run --project src/MapGen.Cli -- mask-cell` with the slice's
  examples prints the expected mask; an out-of-bounds cell exits non-zero with the
  failure named.
- **Status:** todo.

## Task 10 — Compatibility evidence (optional golden recompute)

- **What:** Optionally add a compatibility test that recomputes masks from a golden
  `.heightmap` with `AdjacencyMaskCalculator.ComputeMasks` and confirms each appears in
  the corresponding golden `.maptiles` tile-id low nibbles. The per-cell evidence
  against the real legacy binary is Task 2's adapter; see `acceptance.md` for the full
  evidence strategy. Left as an option for the implementer to add if the BDD nibble
  probe is judged insufficient.
- **Outputs:** `tests/MapGen.CompatibilityTests`.
- **Validation:** `just test-compatibility` — green.
- **Status:** todo (optional).

## Task 11 — Same Gherkin green on the net profile

- **What:** Wire the `net` profile adapter to `MapGen.Cli mask-cell` so all five
  scenarios (including `@net-only` rejection) pass from the same feature file with the
  same grids used on the `legacy` profile.
- **Outputs:** `net` adapter under `tests/bdd/support/`.
- **Validation:** `just bdd-net` — all five scenarios green.
- **Status:** todo.

## Task 12 — Full gate ladder and promotion

- **What:** Run the whole quality surface, then promote: append
  `@slice-02-adjacency-mask` to `specs/dafny-ready.tags` and `tests/bdd/net-ready.tags`
  in this PR, with the charter exit criteria met (see `acceptance.md`).
- **Outputs:** updated promotion ledgers; PR evidence per `acceptance.md`.
- **Validation:** `just quality` — every gate green (format, build, verify, unit,
  architecture, compatibility, BDD smoke + legacy) plus `just bdd-net`.
- **Status:** todo.
