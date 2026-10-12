# Haxe pilot — cell-to-tile and adjacency-mask domain implementation

Issues #107 (cell-to-tile) and #117 (adjacency-mask). Haxe is the proposed
canonical source language for pipeline components going forward; each stage
compiles its shared Haxe domain code to whichever runtime target fits that
stage. This directory proves that idea against two already-closed Tiler
slices (`docs/specs/01-cell-to-tile/`, M3; `docs/specs/02-adjacency-mask/`,
M4) — it does not replace anything.

## Source ownership

- `domain/tileresolution/` — shared Haxe domain code. No target-specific
  types, no IO, no clock. This is the only place these rules are
  hand-written in Haxe; each file mirrors its
  `src/MapGen.Domain/TileResolution/*.cs` twin one file at a time, by
  design, so a reviewer can diff the two.
  One known divergence: Haxe `CellMapDimensions` rejects width or height
  above `MaxSafeDimension` (2^30) to keep tile coordinates inside 32-bit
  `Int`; the C# twin does not yet. See the slice's `verification-report.md`.
- `stages/<stage>/` — one directory per pipeline stage. Holds that stage's
  build command (`build-<target>.hxml`) and a thin target-specific entry
  point (`Main.hx`). Domain behaviour never lives here — see
  `stages/tiler/Main.hx`'s docblock for the rule this enforces.
- `tests/` — Haxe-side checks of the shared domain code against the two
  existing references (below). Not a replacement test suite; a third witness.
- `stages/<stage>/generated-cs/` (and any other `generated-*` directory) is
  Haxe compiler **output**, gitignored. It is never hand-edited and never a
  second implementation to maintain — if it looks wrong, fix the Haxe source
  under `domain/` and rebuild.

## How to add a stage

1. Add `stages/<stage>/Main.hx` — a thin adapter: parse the stage's real
   input, call shared `domain/` code, write the stage's real output format.
   No domain rule may live in `Main.hx`.
2. Add `stages/<stage>/build-<target>.hxml` choosing a target (below).
3. Prove behaviour against the stage's existing references (Dafny model
   and/or Gherkin feature and/or golden fixtures) the same way
   `tests/TileResolutionTest.hx` does for Tiler's cell-to-tile rule — one
   named check per lemma or scenario, not a rewritten contract.
4. Do not remove or edit the legacy implementation until parity is
   demonstrated and reviewed.

## Target selection

Provisional, per stage, until representative workloads are benchmarked:

- **cs** (this pilot) — chosen for Tiler because Tiler's own runtime is
  already C#/.NET, so a later integration step compares same-language output
  instead of also crossing a language boundary.
- **cpp** — candidate for native, compute-heavy stages (Heightmap,
  WeatherAnalyses are Rust today; cpp is Haxe's closest analogue).
- No Rust backend: Haxe does not generate Rust. Any stage currently in Rust
  that moves to Haxe picks cs or cpp instead.

## Toolchain note: bypassing hxcs's own build step

Haxe's `cs` target (via the `hxcs` haxelib, 4.2.0 as installed) defaults to
`-D NET_20` and, left to itself, tries to finish the build by shelling out to
`mono`/`csc` directly — neither is installed on this machine, and even if
they were, that path produces a legacy-Mono binary, not SDK-style `net10.0`
output.

`build-cs.hxml` passes `-D no-compilation`, which stops Haxe after emitting
C# source and skips that invocation entirely. `HaxeTilerPilot.csproj` (hand-
maintained, tracked — NOT generated) then compiles that source with the same
`dotnet build` used for the rest of this repository's .NET projects. The
generated `haxe.lang.*` / `cs.internal.*` runtime shim classes that `hxcs`
emits alongside the domain code compile cleanly under net10.0 as plain C# —
no `mono`, no `csc`, no legacy-runtime target needed:

```sh
cd haxe
haxe stages/tiler/build-cs.hxml                        # emit C# source only
dotnet build stages/tiler/HaxeTilerPilot.csproj         # compile it, net10.0
dotnet stages/tiler/bin/Debug/net10.0/HaxeTilerPilot.dll
# -> cell (3,4) -> (6,8), (7,8), (6,9), (7,9)
```

That output matches the Gherkin "Expand an interior cell" scenario and
`CellExpanderPropertyTests`'s expectation for the same input exactly.

This resolves the earlier concern about the `cs` target needing a legacy
runtime — it doesn't, once `hxcs`'s own build invocation is skipped. It does
NOT mean the generated code is reviewed as production-quality or wired into
the real Tiler build (`RTSColonyTerrainGenerator.sln`); `HaxeTilerPilot.csproj`
is a standalone proof project, intentionally outside both `.sln` files.

## Running this pilot

```sh
cd haxe
haxe tests/build-test.hxml                        # behavioural checks, interpreted
haxe stages/tiler/build-cs.hxml                    # emit C# source
dotnet build stages/tiler/HaxeTilerPilot.csproj    # compile the emitted source, net10.0
```
