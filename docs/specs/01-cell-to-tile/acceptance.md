# Acceptance: 01-cell-to-tile

<!-- Lifecycle steps 8 and 9: acceptance gates and PR evidence. -->

The gates that must hold before the closing PR for issue #7 (milestone M3,
tag `@slice-01-cell-to-tile`). This file feeds the PR summary format in `AGENTS.md`.
Done means the charter's exit criteria
(`mapgen-spec-driven-planning/08-first-epic-verified-cell-to-tile.md`) plus
promotion, all of it evidenced below.

## Behavioural Gates (dual profile)

- Feature file: `tests/bdd/features/01-cell-to-tile/cell-to-tile-expansion.feature`
  (the charter's four scenarios).
- `npm run bdd:legacy` (the legacy pipeline): scenarios 1–3 green — proves the
  contract is captured correctly against the baseline.
- `npm run bdd:net` (new C# implementation via `MapGen.Cli expand-cell`): all four
  scenarios green — proves the slice is ported.
- **Approved profile asymmetry:** the rejection scenario is tagged `@net-only`. The
  legacy stage has no per-cell request surface to reject a single cell — it expands
  whole maps — so rejection is a property of the new command boundary, not a
  behaviour the baseline can exhibit. Scenarios 1–3 are the parity claim; scenario 4
  is deliberately `net`-only and documented here so it is never mistaken for missing
  coverage.
- Attach or link the cucumber report for both profiles as PR evidence.

## Formal Gates (Dafny)

- `dafny verify specs/tiling/CellToTile.dfy` (via `just verify`): all obligations
  discharged — exactly-four, uniqueness, in-bounds, exact corner coordinates in the
  contractual order, and doubled tile-map dimensions. Determinism is structural
  (Dafny functions are pure), so it carries no lemma; the report must say so rather
  than imply it was proved separately.
- `verification-report.md` present in this directory and honest about assumptions
  and exclusions (human-authored after the verification run).

## Compatibility Evidence

Compatibility with the legacy baseline is demonstrated by three lanes, each honest
about what it does and does not prove:

- **(a) Dimension doubling — golden jobs.** The golden fixtures already prove the
  doubling behaviourally: 64×64-cell golden jobs
  (`43860dcf-6469-42a7-9843-4e33abeacfac`, `3c96b74c-6f86-4d27-a0ca-c567f385ae8e`,
  `0860a05a-a410-4cc2-987d-a48a4cd120c7`) produced 128×128-tile `.maptiles`,
  asserted by the header check in `tests/MapGen.CompatibilityTests`. This proves the
  map-level consequence of the rule, not the per-cell mapping.
- **(b) Per-cell expansion — the real legacy binary.** The BDD `legacy` profile
  synthesizes a 10×10 `.heightmap` in which only the target cell carries a
  distinctive terrain value, runs the prebuilt binary
  `MapGenerator/Tiler/bin/published/Tiler` (usage: `Tiler <heightmap>`, writing
  `./outbox/<id>.maptiles` relative to CWD), and asserts exactly four tiles carry
  that terrain byte, at exactly the four expected coordinates — the legacy tile id
  is `terrain << 8 | mask`, so the terrain byte identifies the cell's region. The
  same Gherkin green on both profiles for scenarios 1–3 is the per-cell parity
  claim.
- **(c) Rejection — not comparable, by design.** The out-of-bounds scenario cannot
  be replayed against the legacy stage (no per-cell surface); it is `@net-only`.
  Disposition: contract of the new command boundary, approved asymmetry — not a
  normalization and not a weakening.

No differences between the charter order and the legacy order exist: the legacy
resolver (`MapGenerator/Tiler/Processing/TileIdResolver.cs` lines 85–96) emits
TL, TR, BL, BR, which the contract adopts verbatim. Order is compared, never
normalized away.

## Test Evidence

- `just test-unit` — unit examples (boundary and invalid inputs from the charter's
  test plan) and FsCheck properties mirroring the Dafny lemmas: green.
- `just test-architecture` — dependency purity across Domain, Application, Cli:
  green.
- `just test-compatibility` — golden-fixture harness plus the dimension-doubling
  header check: green.
- `just quality` — the whole gate ladder (format, build, verify, unit,
  architecture, compatibility, BDD smoke + legacy): green.
- New regression tests for any bug corrected en route.

## Manual Checks

- Read the cucumber reports side by side and confirm scenarios 1–3 ran through both
  adapters (the legacy run should show the synthesized heightmap and the binary
  invocation; the net run should show the CLI invocation). "Looks right" means the
  same scenario text, two different processes, identical coordinate tables.
- Inspect one legacy-adapter scratch directory: the `.maptiles` in `outbox/` should
  contain exactly four tiles whose high byte is the marker terrain value, at the
  expected coordinates, and nowhere else.
- Read `verification-report.md` for honesty: assumptions and unproved properties
  named, no claim that determinism was proved as a lemma.

## Promotion

- [ ] `@slice-01-cell-to-tile` appended to `tests/bdd/net-ready.tags` (this PR)
- [ ] `@slice-01-cell-to-tile` appended to `specs/dafny-ready.tags` (this PR)
- [ ] No specification was weakened without human approval (or the weakening is
      named in the PR as a `Specification correction`).

## Known Gaps and Follow-Ups

- Rejection behaviour is proved for the new boundary only (see the `@net-only`
  asymmetry above); the legacy pipeline offers nothing to compare against, and no
  follow-up can change that.
- Tile id composition (`terrain << 8 | mask`) and adjacency-mask derivation are
  exercised only incidentally by the marker-byte technique; their own slices carry
  their contracts (tracked under milestone M3 follow-on issues).
- The golden-job compatibility check asserts the dimension header, not tile-by-tile
  contents; full `.maptiles` logical comparison arrives with the slice that ports
  tile id composition (the skipped `Replacement_tiler_matches_legacy_on_golden_jobs`
  test in `tests/MapGen.CompatibilityTests` marks the spot).
- `MapGen.Cli` is a test seam, not the future Tiler stage entry point; designing the
  stage executable is a later slice.
