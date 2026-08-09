# StargusExport

Export stage that converts a World Payload into a StarCraft I map artifact.

## Input
- World payload JSON file (TreePlanter output) placed in `inbox/` or provided via CLI.
- Expected fields: `map.width_in_cells`, `map.height_in_cells`, `tiles[]` with `x`, `y`, and `terrain`.

## Output
- `outbox/<job_id>.chk` (raw Scenario.chk data)
- `outbox/<job_id>.scm` (MPQ archive containing `staredit/scenario.chk`)
- `exports/<job_id>.scm` and `exports/last_map_<job_id>.scm` (validated/staged copies)
- `maps/MapGeneratorOutput/<job_id>.smp` + `.sms` (Stargus-native maps generated via `startool`)

## Notes
- Stargus requires `.scm`/`.scx` MPQ archives that contain a `staredit/scenario.chk` file.
- This stage writes the `CHK` payload first, then always packages a valid `.scm`.
- If `--mpq-tool` is provided, it will be used; otherwise a minimal MPQ writer is used.
- Tile mapping is configurable via a JSON mapping file.

## Tile Mapping
Default mapping: `tileset_mappings/default_badlands.json` (tileset: jungle)

Format:
```json
{
  "tileset": "jungle",
  "default_tile": 0,
  "terrain_to_tile": {
    "grass": 0,
    "dirt": 0,
    "rock": 0,
    "water": 0,
    "ridge": 0
  }
}
```

## Running
- Manual:
  - `./stargus-exporter --job-file <payload.json> --output-dir outbox`
- Wrapper:
  - `bin/consume_stargusexport_job.sh`

## Stargus Local Setup (Notes)
- Stargus uses `.scm` MPQ maps under its data directory `maps/` folder.
- Default auto-copy targets (first existing):
  - `~/.stratagus/sc/maps`
  - `~/.stratagus/stargus/maps`
  - `~/.local/share/stratagus/sc/maps`
  - `~/.local/share/stratagus/stargus/maps`
- Override with `STARGUS_MAPS_DIR=/path/to/maps` when running the wrapper.
- Exported maps go into a subfolder named `MapGeneratorOutput` by default so they appear as a separate entry in the Select Scenario list. Override with `STARGUS_MAPS_SUBDIR`.
- The exporter will attempt to convert `.scm` into `.smp/.sms` using `startool` (set `STARGUS_STARTOOL` to override).
- Use `STARGUS_TEMPLATE_SCM=/path/to/Template.scm` to base output on a known-good map with start locations.
 - Validation defaults: MPQ header signature + minimum size (10KB). Override with `MIN_SCM_BYTES`.

## Logs
- `outbox/<job_id>.stargus-export.log` captures validation + copy status.

## Validation Helper
Run a quick MPQ header/size sanity check:
```bash
bin/validate_scm.sh outbox/<job_id>.scm
```
This also validates that `staredit/scenario.chk` exists in the MPQ.

## Tracking A Full Run
Run the pipeline and follow progress (including Stargus export):
```bash
MapGenerator/bin/trace_pipeline.sh
```
For follow-only mode (no new job):
```bash
FOLLOW_ONLY=1 MapGenerator/bin/trace_pipeline.sh
```
You can override the minimum size:
```bash
MIN_SCM_BYTES=20480 bin/validate_scm.sh outbox/<job_id>.scm
```
- If Stargus has not been run yet, the data directory may not exist.

### Example (auto-copy)
```
STARGUS_MAPS_DIR="$HOME/.stratagus/sc/maps" bin/consume_stargusexport_job.sh
```

## TYS Checklist
- Run the wrapper once and verify:
  - `outbox/<job_id>.chk` exists
  - If MPQ tool is installed, `outbox/<job_id>.scm` exists
  - File sizes are non-zero
