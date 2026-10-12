# Haxe pilot — cell-to-tile domain implementation

Issue #107. Haxe is the proposed canonical source language for pipeline
components going forward; each stage compiles its shared Haxe domain code to
whichever runtime target fits that stage. This directory is the first,
narrow proof of that idea against one already-closed slice
(`docs/specs/01-cell-to-tile/`, milestone M3) — it does not replace anything.

## Source ownership

- `domain/tileresolution/` — shared Haxe domain code. No target-specific
  types, no IO, no clock. This is the only place the cell-to-tile rule is
  hand-written in Haxe; it mirrors `src/MapGen.Domain/TileResolution/*.cs`
  one file at a time, by design, so a reviewer can diff the two.
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
  WeatherAnalyses are Rust today; cpp is Haxe's closest analogue). Issue
  #119 benchmarked this (below): on a representative workload, `cpp` ran
  ~10-11x faster than `cs`, with byte-identical output.
- No Rust backend: Haxe does not generate Rust. Any stage currently in Rust
  that moves to Haxe picks cs or cpp instead.

## Benchmark: cpp vs cs (issue #119)

`benchmarks/faultline/` is a synthetic, representative workload for
comparing targets — **not** a port of the real Rust `heightmap-engine`
(`MapGenerator/Heightmap`). It is shaped like that family of stages (tight,
allocation-light, per-cell integer loop over a grid, run many times): classic
fault-formation terrain generation, picking a random line through the grid
and raising one side / lowering the other, for a fixed number of passes. The
line-side test is an integer cross product (no floating point), so the exact
same seed produces byte-identical output on every target — the thing this
benchmark needs in order to tell "faster" apart from "different algorithm."

```sh
cd haxe
haxe benchmarks/faultline/build-cs.hxml
dotnet build benchmarks/faultline/HaxeFaultLineBenchmark.csproj -c Release
dotnet benchmarks/faultline/bin/Release/net10.0/HaxeFaultLineBenchmark.dll

haxe benchmarks/faultline/build-cpp.hxml    # -D release; needs hxcpp (haxelib install hxcpp)
./benchmarks/faultline/generated-cpp/Main
```

Both run the same workload: a 512x512 grid, 3000 fault passes, seed
`20261012`, best-of-3 trials. Measured on this machine:

| Target | Best trial | Checksum |
|---|---|---|
| `cpp` (`-D release`) | ~860ms | `-343056495` |
| `cs` (`dotnet build -c Release`, net10.0) | ~9.0-9.3s | `-343056495` |

Checksums matched on every run across repeated trials — both targets did
identical work. `cpp` was consistently **~10-11x faster**.

**Recommendation:** for a compute-heavy, tight-loop stage like Heightmap or
WeatherAnalyses, `cpp` is the better-fitting target, not `cs`. The `cs`
target's overhead here almost certainly comes from `hxcs`'s `haxe.lang.*`
runtime shim (boxing/dynamic dispatch around what should be plain array
indexing) rather than from .NET itself being slow — Tiler's own hand-written
C# runs at native .NET speed; it is only Haxe's *generated* C# that pays this
cost. That is a reason to keep `cs` for stages like Tiler, where the
per-cell work is small and already wrapped in C#'s own ecosystem, and to
prefer `cpp` once a stage's inner loop is the actual cost center. This one
workload is not a verdict on every future stage — benchmark again with that
stage's real shape before committing to a target.

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
