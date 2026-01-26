# StargusExport

Export stage that converts a World Payload into a StarCraft I map artifact.

## Input
- World payload JSON file (TreePlanter output) placed in `inbox/` or provided via CLI.
- Expected fields: `map.width_in_cells`, `map.height_in_cells`, `tiles[]` with `x`, `y`, and `terrain`.

## Output
- `outbox/<job_id>.chk` (raw Scenario.chk data)
- `outbox/<job_id>.scm` (MPQ archive containing `staredit/scenario.chk`)

## Notes
- Stargus requires `.scm`/`.scx` MPQ archives that contain a `staredit/scenario.chk` file.
- This stage writes the `CHK` payload first, then always packages a valid `.scm`.
- If `--mpq-tool` is provided, it will be used; otherwise a minimal MPQ writer is used.
- Tile mapping is configurable via a JSON mapping file.

## Tile Mapping
Default mapping: `tileset_mappings/default_badlands.json`

Format:
```json
{
  "tileset": "badlands",
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

## TYS Checklist
- Run the wrapper once and verify:
  - `outbox/<job_id>.chk` exists
  - If MPQ tool is installed, `outbox/<job_id>.scm` exists
  - File sizes are non-zero
