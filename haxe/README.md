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

## Known toolchain limitation (this pilot)

`haxe stages/tiler/build-cs.hxml` successfully **generates** C# source
(`stages/tiler/generated-cs/src/*.cs`) — inspected and confirmed correct: it
calls `CellExpander.expand` and produces the expected result. It does **not**
finish compiling to an executable here, for two independent reasons worth
separating before choosing how to fix either:

1. Haxe's `cs` target (via the `hxcs` haxelib, 4.2.0 as installed) defaults to
   `-D NET_20` and emits its own `haxe.lang.*` runtime shim classes — it is
   not, out of the box, SDK-style `net10.0` source. Dropping it into
   `src/Tiler`'s actual `.csproj` is not a drop-in; it needs either newer
   `net-ver`/SDK-support flags on the Haxe side or a deliberate bridge, not
   assumed as part of this pilot.
2. No `mono` or `csc` is installed on this machine to finish even the
   default legacy build, so the generated source has not been executed, only
   read and reasoned about. `dotnet` is installed but is not what `hxcs`
   invokes.

Resolving either is future work, not assumed here. The behavioural proof in
this pilot rests on `tests/TileResolutionTest.hx`, run under Haxe's own
interpreter (`--interp`), which needs neither mono nor csc.

## Running this pilot

```sh
cd haxe
haxe tests/build-test.hxml       # behavioural checks, interpreted — see output below
haxe stages/tiler/build-cs.hxml  # generates C# source; does not compile it (see above)
```
