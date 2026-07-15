# Acceptance: 02-adjacency-mask

<!-- Lifecycle steps 8 and 9: acceptance gates and PR evidence. -->

The gates that must hold before the closing PR for issue #10 (milestone M4, tag
`@slice-02-adjacency-mask`). This file feeds the PR summary format in `AGENTS.md`.
Done means the charter's exit criteria plus promotion, all of it evidenced below.

## Behavioural Gates (dual profile)

- Feature file: `tests/bdd/features/02-adjacency-mask/adjacency-mask.feature` (the
  slice's five scenarios).
- `npm run bdd:legacy` (the legacy pipeline): scenarios 1–4 green — proves the mask
  rule is captured correctly against the baseline.
- `npm run bdd:net` (new C# implementation via `MapGen.Cli mask-cell`): all five
  scenarios green — proves the slice is ported.
- **Approved profile asymmetry:** the rejection scenario is tagged `@net-only`. The
  legacy stage has no per-cell request surface to reject a single cell — it masks whole
  maps — so rejection is a property of the new command boundary, not a behaviour the
  baseline can exhibit. Scenarios 1–4 are the parity claim; scenario 5 is deliberately
  `net`-only and documented here so it is never mistaken for missing coverage.
- Both profiles run identical grids for scenarios 1–4, with terrain values in `[0, 3]`
  (the legacy `HeightmapReader` bound). Attach or link the cucumber report for both
  profiles as PR evidence.

## Formal Gates (Dafny)

- `dafny verify specs/tiling/AdjacencyMask.dfy` (via `just verify`): all obligations
  discharged — `MaskInRange`, `EdgeCellsNeverSetOffMapBits`, `EastWestSymmetry`,
  `NorthSouthSymmetry`, and `BitsReflectNeighbourPredicate` (15 obligations, 0 errors
  at authoring). Determinism is structural (Dafny functions are pure), so it carries no
  lemma; the report must say so rather than imply it was proved separately.
- `verification-report.md` present in this directory and honest about assumptions and
  exclusions (human-authored after the verification run).

## Compatibility Evidence

Compatibility with the legacy baseline is demonstrated by two lanes, each honest about
what it does and does not prove:

- **(a) Per-cell mask — the real legacy binary.** The BDD `legacy` profile synthesizes
  a small `.heightmap` with the scenario's terrain layout (terrain in `[0, 3]`), runs
  the prebuilt binary `MapGenerator/Tiler/bin/published/Tiler` (usage: `Tiler
  <heightmap>`, writing `./outbox/<id>.maptiles` relative to CWD), and reads the target
  cell's mask as the low nibble (`id & 0x0F`) of any one of its four 2×2 tiles — the
  legacy tile id is `terrain << 8 | mask`, so the low nibble is the mask. The same
  Gherkin green on both profiles for scenarios 1–4 is the per-cell parity claim.
- **(b) Golden recompute — optional.** A compatibility test may recompute masks from a
  golden `.heightmap` (`43860dcf-6469-42a7-9843-4e33abeacfac`,
  `3c96b74c-6f86-4d27-a0ca-c567f385ae8e`, `0860a05a-a410-4cc2-987d-a48a4cd120c7`) with
  `AdjacencyMaskCalculator.ComputeMasks` and confirm each mask appears in the
  corresponding golden `.maptiles` tile-id low nibbles. This proves the rule against
  pinned real-map data at scale, complementing the small synthetic BDD grids. Left as
  an option for the implementer (see `tasks.md`, Task 10); if omitted, the BDD nibble
  probe stands as the compatibility evidence and the omission is noted in the PR.
- **(c) Rejection — not comparable, by design.** The out-of-bounds scenario cannot be
  replayed against the legacy stage (no per-cell surface); it is `@net-only`.
  Disposition: contract of the new command boundary, approved asymmetry — not a
  normalization and not a weakening.

No differences between the slice's contract and the legacy rule exist: the bit weights
(N=1, E=2, S=4, W=8), the existence-and-same-terrain guards, and the row-major order
are adopted verbatim from `CellBitmaskCalculator.cs`. Masks are compared as read from
the low nibble, never normalized away.

## Test Evidence

- `just test-unit` — unit examples (interior → 15, corner → 6, differing terrain → 0,
  single-axis edges) and FsCheck properties mirroring the Dafny lemmas (range, bits
  reflect predicate, edge cells set no off-map bit, East⇔West and South⇔North
  symmetry, repeat-call determinism): green.
- `just test-architecture` — dependency purity across Domain, Application, Cli, and the
  Mediator handler-interface check
  (`Request_handlers_implement_the_mediator_handler_interface`): green.
- `just test-compatibility` — golden-fixture harness (plus the optional mask recompute
  if added): green.
- `just quality` — the whole gate ladder (format, build, verify, unit, architecture,
  compatibility, BDD smoke + legacy): green.
- New regression tests for any bug corrected en route.

## Manual Checks

- Read the cucumber reports side by side and confirm scenarios 1–4 ran through both
  adapters (the legacy run should show the synthesized heightmap and the binary
  invocation; the net run should show the `mask-cell` CLI invocation). "Looks right"
  means the same scenario text, two different processes, identical mask values.
- Inspect one legacy-adapter scratch directory: the `.maptiles` in `outbox/` should
  carry the expected low nibble at the target cell's four tiles, and the corner-cell
  scenario should show no North or West bit set.
- Read `verification-report.md` for honesty: assumptions and unproved properties named,
  no claim that determinism was proved as a lemma, and the two symmetry lemmas named
  explicitly.

## Promotion

- [ ] `@slice-02-adjacency-mask` appended to `tests/bdd/net-ready.tags` (this PR)
- [ ] `@slice-02-adjacency-mask` appended to `specs/dafny-ready.tags` (this PR)
- [ ] No specification was weakened without human approval (or the weakening is named
      in the PR as a `Specification correction`).

## Known Gaps and Follow-Ups

- Rejection behaviour is proved for the new boundary only (see the `@net-only`
  asymmetry above); the legacy pipeline offers nothing to compare against, and no
  follow-up can change that.
- The mask is observed through the packed tile id (`terrain << 8 | mask`); tile-id
  composition as a rule of new code is a later slice, exercised here only as the
  observation channel for the low nibble.
- Legacy-profile grids are bound to terrain `0..3` by the `HeightmapReader`; the wider
  terrain-equality domain is exercised only by unit and property tests, not by the
  cross-profile scenarios.
- `MapGen.Cli mask-cell` is a test seam, not the future Tiler stage entry point;
  designing the stage executable is a later slice.
