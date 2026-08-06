# RTS Colony Terrain Generator — Context

Glossary of the ubiquitous language for the map-generation pipeline. This file is a
glossary only: it defines what terms mean, not how anything is implemented. The same
terms should appear in requirements, Gherkin scenarios, Dafny models, C# types, logs,
and pull requests.

## The grid

**Cell**:
One unit of the terrain grid that Heightmap generates and WeatherAnalyses annotates. A
cell carries height and derived analysis values (slope, flow, wetness) at a coordinate
`(x, y)` inside the cell-map dimensions declared by the job spec.
_Avoid_: "pixel" (a debug-render concern); "tile" (a cell is upstream of tiles);
"square" (unscoped).

**Tile**:
One unit of the renderable/simulation grid that Tiler emits in `<id>.maptiles`. Tiles
carry a tile identifier and adjacency mask and exist on a grid twice the cell
dimensions in each axis. Downstream stages (TreePlanter onward) and the final
64×64 map-document payload speak in tiles.
_Avoid_: using "tile" for a terrain cell; "sprite" (an asset, not a grid unit).

**Cell-to-Tile Expansion**:
The deterministic rule that one cell at `(x, y)` produces exactly the four unique tile
coordinates of its 2×2 tile region — `(2x, 2y)` through `(2x+1, 2y+1)` — all inside a
tile map of `width×2` by `height×2`. The first verified vertical slice; the canonical
example of a rule that gets a Dafny proof.
_Avoid_: "upscaling", "doubling" (both hide the exact-four-unique-in-bounds contract).

## The pipeline

**Stage**:
One isolated, deterministic transformer under `MapGenerator/<StageName>/` that
communicates only via files: it reads one job from its inbox, writes its authoritative
output to its outbox, and moves the input to archive or failed. Stages are
language-agnostic (Rust, C#, PHP, Kotlin, Python…) behind a bash entrypoint and a
systemd path watcher. The current stages are Heightmap, WeatherAnalyses, Tiler,
TreePlanter, WorldFeatures, PathFinder, Playable, WorldSnapshot, WorldPreview,
WorldTilemap, StargusExport, AncientCivilization, CartridgeManufacturer,
CivicOverreach, SimulateCity, TransportTycoonDeluxe, and InfrastructureBuilder
(planned). See `docs/Stage_Contract.md`.
_Avoid_: "service" (implies long-running network processes); "step" (reserve for
Gherkin steps); equating a Stage with a Bounded Context (see below).

**Lane**:
One of the queue directories every stage owns: `inbox/` (immutable incoming jobs),
`outbox/` (authoritative outputs downstream stages may trust blindly), `failed/`
(preserved inputs of failed jobs), `archive/` (inputs of completed jobs). `debug/` is
human-facing and carries no correctness guarantees.
_Avoid_: "queue" for a specific directory (a lane is one directory; the queue is the
mechanism); writing to another stage's inbox except as the documented handoff.

**Artifact**:
A committed file or directory in a stage outbox — `<id>.heightmap`, `<id>.weather`,
`<id>.maptiles`, `<id>.worldpayload/`, `<id>.playable.json`, `<id>.wcar`, `<id>.png`.
Committed artifacts are immutable; temporary files must never be presentable as
committed artifacts; a stage is successful only when its artifact is committed and
validated.
_Avoid_: "output file" for a half-written temp file; "artifact" for debug renders.

**Job**:
One map-generation request, identified by an `<id>` that correlates every artifact,
lane movement, and log line across all stages. One job = one input file per stage.
_Avoid_: "task", "ticket" (reserve those for issue tracking); reusing an `<id>`.

**Golden Job**:
A pinned job whose archived inputs and outbox artifacts are kept as fixtures. Golden
Jobs are the concrete data Compatibility Tests replay against both the legacy stage
and its replacement. Deleting or regenerating a Golden Job's fixtures is a
specification change requiring human approval.
_Avoid_: "test data" (unpinned, regenerable); "sample job".

## The migration method

**Slice**:
One vertical feature moved through the full lifecycle (requirement → BDD → contract →
Dafny → C# → tests). One slice = one sprint = one Gitea issue = one branch
`feature/<issue>-<slug>` = one Spec Pack. The first slice is Verified Cell-to-Tile
Expansion.
_Avoid_: "phase" (phases are the M1–M9 milestones grouping slices); "epic" for a
single slice.

**Legacy Pipeline (the baseline)**:
The runnable legacy stages treated as the executable specification of current
behaviour during migration: whatever they do is, by definition, correct until a
Behaviour correction says otherwise. Read and run freely; never modify to make a test
pass. The same stance The-Pulse takes toward its Node backend.
_Avoid_: "oracle" (upstream Pulse docs use that word for this same concept; it is
banned in local docs as confusing); "legacy code" (implies it may be wrong); "the old
stage" (it is the reference truth, not merely old).

**Verified Model**:
The second reference: a Dafny Level A model (executable mathematical model) or Level B
verified reference implementation under `specs/`, machine-checked for the
correctness-critical rules of a slice. The Legacy Pipeline answers "what does the
system do today?"; the Verified Model answers "what must always be true, for all valid
inputs?". A C# implementation must agree with both — the dual-reference design
(ADR 0002).
_Avoid_: "mathematical oracle" (banned "oracle" vocabulary); "the proof" for the whole
model (proofs are lemmas inside it); "spec" bare (ambiguous with Spec Pack and with
Gherkin).

**Contract**:
The framework-free statement of a domain operation: preconditions, postconditions,
invariants, determinism and idempotency claims, and valid failures. Contracts live in
the slice's Spec Pack and are the source both the Dafny model and the C# domain types
encode. Weakening a contract to make verification or tests pass is prohibited.
_Avoid_: "interface" (a C# artifact); confusing with the Stage Contract
(`docs/Stage_Contract.md`), which governs stage directory structure, not domain rules.

**Spec Pack**:
The durable, per-slice document set at `docs/specs/<NN-slice-name>/`:
`requirements.md`, `design.md`, `tasks.md`, `acceptance.md` (plus
`verification-report.md` once Dafny work lands). Clear enough that a human or agent
can pick up the slice without the originating conversation. See
`docs/specs/spec-driven-development/README.md`.
_Avoid_: "the spec" bare; "PRD" for the whole pack (requirements.md is the PRD-shaped
part).

**Promotion**:
The explicit, reviewable act of declaring a slice done, performed in the closing PR by
appending the slice's tag to the promotion ledgers: `specs/dafny-ready.tags` (the
slice's Dafny rules verify and gate CI) and `tests/bdd/net-ready.tags` (the slice's
Gherkin must pass against the new C# backend). Tags not yet listed are expected to be
red on the new backend. Mirrors The-Pulse's `net-ready.tags` allowlist.
_Avoid_: "enabling the tests" (promotion is a reviewed declaration, not a toggle);
promoting outside a PR.

**Bounded Context**:
A boundary of language, rules, and ownership — not automatically a pipeline stage. The
proposed contexts (see `mapgen-spec-driven-planning/05-bounded-contexts-and-ownership.md`)
are: Pipeline Lifecycle, Terrain Generation, Weather Analysis, Tile Resolution,
Vegetation Planning, World Features, Traversal and Access, and Artifact Registry.
_Avoid_: one-context-per-stage mapping; a shared "Map" model spanning contexts.

## Overnight delivery

**TheNightCrew**:
The coordinator that decides which approved work is available to which Worker and
records claims and progress. It does not execute repository work.
_Avoid_: "runner", "agent", or using TheNightCrew for the whole delivery system.

**MapGen Night-Crew Worker**:
The repository-aware executor that claims approved MapGen work, performs it in
isolation, and reports progress and evidence to TheNightCrew.
_Avoid_: "TheNightCrew" when referring to the process that edits or tests code.

**Night Crew system**:
The complete overnight delivery capability formed by TheNightCrew and one or more
MapGen Night-Crew Workers.
_Avoid_: "TheNightCrew" for the combined coordinator-and-worker capability.

**Gitea Issue**:
The human-facing agreement for one Slice's approved scope, acceptance criteria, and
delivery lifecycle.
_Avoid_: "Bead" or "NightCrew Job" for approved scope and acceptance criteria.

**Planning Document**:
The versioned repository record that explains one Slice's requirements, design, and
verification expectations.
_Avoid_: chat history, a Bead description, or an issue comment as the durable design.

**Bead**:
The dependency and readiness representation of exactly one approved Slice. It points
to its Gitea Issue and Planning Document but does not redefine their scope.
_Avoid_: using a Bead as an independently executable task without its linked records.

**NightCrew Job**:
The runtime claim and execution record for one eligible Slice. It is not a backlog
item and cannot change the Slice's approved scope or acceptance criteria.
_Avoid_: bare "Job", which means a map-generation request in this context.

**Approved Slice**:
A planned Slice that Craig has explicitly authorized the Night Crew system to execute.
Planning completeness and dependency readiness do not imply approval.
_Avoid_: "ready" without distinguishing human approval from dependency readiness.

## Evidence

**Compatibility Test**:
A test that replays Golden Job fixtures through both the legacy stage and its
replacement (or the Dafny reference) and compares outputs at the logical level,
ignoring non-contractual metadata such as timestamps. Normalizing away meaningful data
to force a match is prohibited.
_Avoid_: "parity test" (Parity is the slice-level claim; this is one evidence lane);
byte-for-byte comparison when the contract is logical.

**Parity**:
The slice-level claim that the same Gherkin feature file is green against both
profiles — the Legacy Pipeline (`legacy`) and the new C# implementation (`net`). Parity
plus a verified Dafny model is the "done" bar for a ported slice.
_Avoid_: "parity" for visual similarity of rendered maps; claiming parity from unit
tests alone.

**Probe**:
A behavioural question asked of the Legacy Pipeline through its real binary and
artifacts — synthesize a minimal input, run the published stage executable, read the
answer out of the artifact it writes (e.g. a marker terrain byte revealing a cell's
tile region; a tile-id low nibble revealing its adjacency mask). The one probe module
is `tests/bdd/support/legacy_tiler_probe.js`; slice adapters own only their
interpretation of the probed artifact.
_Avoid_: "simulation" or "stub" (a probe runs the real legacy executable, never an
imitation of it); re-implementing legacy behaviour in test code and calling it legacy
evidence.

**Persona**:
A named member of the BDD suite's cast — for example an operator submitting a job or
inspecting a failed lane — defined once as data in `tests/bdd/support/personas.js` and
referenced by friendly name in feature files. Destined to become a Screenplay Actor
(with Abilities, Tasks, and Questions) in the planned Serenity/JS evolution (ADR 0003).
_Avoid_: "test user" (personas carry role and intent, not just credentials); defining
persona details inline in step files.
