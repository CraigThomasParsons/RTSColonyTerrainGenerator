# Stage Inventory (Baseline)

Every stage under `MapGenerator/`, as implemented on disk. "Invoked via" names the `bin/`
wrapper and the engine it calls. Filenames use `<id>` for the job id.

| Stage | Language | Invoked via (wrapper → engine) | Consumes | Produces | Responsibility |
|---|---|---|---|---|---|
| **Heightmap** | Rust (+ Python PNG export) | `bin/consume_heightmap_queue_job.sh` → `bin/heightmap-engine` (`heightmap-engine/src/main.rs`); `bin/export_heightmap_png.py` | `Heightmap/inbox/<id>.json` (job spec) | `outbox/<id>.heightmap`; fan-out copies to Tiler + WeatherAnalyses inboxes; PNG + meta to SimulateCity inbox | Fault-line terrain generation → normalized 0–255 height grid + terrain classification |
| **WeatherAnalyses** | Rust | `consume_queue_job.sh` → `bin/weather-engine` (`src/`) | `inbox/<id>.heightmap` | `outbox/<id>.weather` | Derive slope / flow / basin layers from the heightmap |
| **Tiler** | C# / .NET | `bin/consume_tiler_queue_job.sh` → `bin/tiler.sh` → `bin/published/Tiler` (`Program.cs`, `IO/`) | `inbox/<id>.heightmap` | `outbox/<id>.maptiles` | Resolve adjacency bitmasks → final tile ids |
| **TreePlanter** | PHP (Minicli) | `bin/treeplanter.php run` (via `treeplanter.sh`/`run.php`; `src/`) | `<id>.heightmap` + `<id>.maptiles` + `<id>.weather` | `outbox/<id>.worldpayload` (single JSON file) | Assemble tiles + deterministic vegetation → first World Payload |
| **WorldFeatures** | Kotlin / Gradle | `bin/consume_worldfeatures_job.sh` → `gradlew run` | `TreePlanter/outbox/<id>.worldpayload` | `outbox/<id>.worldpayload` (augmented) | Add gameplay features (ramps, mines, resource hints, rivers) |
| **PathFinder** | Kotlin / Gradle | `bin/consume_pathfinder_job.sh` → `gradlew run` (`src/main/kotlin/mapgen/pathfinder/`) | `WorldFeatures/outbox/<id>.worldpayload` | `outbox/<id>.json` (ConnectivityReport; re-embeds tiles + features) | A* connectivity analysis, routes, infrastructure requests |
| **Playable** | Python | `bin/consume_playable_job.sh` → `bin/playable.py` | `WorldFeatures/outbox/<id>.worldpayload` | `outbox/<id>.worldpayload` (copy) + `outbox/<id>.playable.json` | Select deterministic start zones + resource clusters |
| **StargusExport** | Python | `bin/consume_stargusexport_job.sh` → `stargus-exporter` | `Playable/outbox/<id>.worldpayload` (fallback: TreePlanter) | `outbox/<id>.chk` + `<id>.scm` | Export payload to StarCraft CHK/SCM (MPQ) |
| **CartridgeManufacturer** | Rust (cargo workspace) | `bin/consume_cartridge_job.sh` → `wcar_pack`, `wcar_export_chk`, `wcar_run_stratagus` (`bin/wcar-tools/crates/`) | `Playable/outbox/<id>.worldpayload` (fallback: TreePlanter) | `outbox/<id>.wcar` + `<id>.chk` + `<id>.scm` | Pack WCAR cartridge, export CHK/SCM, validate via Stratagus |
| **WorldPreview** | Rust | `bin/consume_worldpreview_job.sh` → `worldpreview-engine` (`bin/worldpreview-engine/src/main.rs`) | `PathFinder/outbox/<id>.json` | `outbox/<id>/index.html` (+ style.css, main.js, world.json, assets/) | Interactive HTML world viewer |
| **WorldSnapshot** | Python (Playwright) | `bin/consume_worldsnapshot_job.sh` → `bin/worldsnapshot.py` | `WorldPreview/outbox/<id>/index.html` | `outbox/<id>.png` | Headless Chromium screenshot of WorldPreview |
| **AncientCivilization** | Rust | `bin/consume_ancientcivilization_job.sh` → `ancientcivilization-engine` | `WorldFeatures/outbox/<id>.worldpayload` | `<id>.settlements.json`, `<id>.ruins.json`, `<id>.ancient_paths.json`, `<id>.reclaimed_resources.json`, `<id>.collapse_reason.txt` | Synthesize ruins / settlements / ancient paths (**largely placeholder content**) |
| **CivicOverreach** | Python | `bin/run_civic_overreach.sh <id>` → `bin/civic_overreach.py` (**no queue consumer**) | `Heightmap/outbox/<id>/` PNG+meta or `<id>.heightmap` | `outbox/<id>.civic_overreach.worldpayload` | Overreach / disaster / ruin heuristics from the heightmap |
| **SimulateCity** | Python | `bin/consume_simulatecity_job.sh` → `bin/run_civic_overreach.sh <id>` → `bin/civic_overreach.py` | `Heightmap/outbox/<id>.heightmap` (latest) | `outbox/<id>.civic_overreach.worldpayload` | Near-duplicate of CivicOverreach with a queue consumer |
| **TransportTycoonDeluxe** | Bash + OpenTTD | `bin/consume_transporttycoondeluxe_job.sh` (scaffold) OR `bin/run_transport_tycoon.sh` (OpenTTD headless) | consume: any file in `inbox/`; run: `inbox/<id>.heightmap.png` | `<id>.transporttycoondeluxe` OR `<id>.transporttycoon.json` (**placeholder**) | Scaffold — drives OpenTTD but does not extract infrastructure yet |
| **WorldTilemap** | *(planned)* Python/pygame | none yet — only `docs/plan.md` | *(planned)* `Playable/outbox/<id>.worldpayload` + `<id>.playable.json` | *(planned)* `outbox/<id>.png` | Planned pygame tilemap renderer (would replace WorldSnapshot) |
| **InfrastructureBuilder** | *(planned)* Kotlin / Gradle | none yet — empty `bin/`, `plan.md`, skeleton `src/` | *(planned)* `PathFinder/outbox/<id>.json` + WorldFeatures `<id>.worldpayload` | *(planned)* `outbox/<id>.worldpayload` (mutated) | Planned — apply PathFinder infrastructure requests (roads / bridges / tunnels) |

**Wired vs planned:** 15 stages have real implementations; **WorldTilemap** and
**InfrastructureBuilder** are scaffolds (directories + plan docs, no engine, not installed).
Of the wired stages, **AncientCivilization** and **TransportTycoonDeluxe** emit largely
placeholder content.
