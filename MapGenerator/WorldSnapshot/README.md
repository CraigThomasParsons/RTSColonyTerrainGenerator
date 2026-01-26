# WorldSnapshot

WorldSnapshot consumes WorldPreview output directories and renders a PNG snapshot of the fully rendered world.

## Outputs

- outbox/<job_id>.png

## Inputs

- WorldPreview outbox directory (default):
  - MapGenerator/WorldPreview/outbox/<job_id>/index.html

## Requirements

- Playwright installed in the project venv:
  - `pip install playwright`
  - `playwright install`

## Install (systemd)

```bash
cd MapGenerator/WorldSnapshot
./install.sh
```

## Run manually

```bash
cd MapGenerator/WorldSnapshot
bin/consume_worldsnapshot_job.sh
```

## Environment overrides

- `WORLD_SNAPSHOT_INPUT_DIR` (default: MapGenerator/WorldPreview/outbox)
- `WORLD_SNAPSHOT_OUTPUT_DIR` (default: MapGenerator/WorldSnapshot/outbox)
- `WORLD_SNAPSHOT_LOG_DIR` (default: logs/jobs)
- `WORLD_SNAPSHOT_TIMEOUT_SECONDS` (default: 20)

## Notes

- The snapshot uses the WorldPreview canvas with UI hidden for a clean capture.
- The camera is normalized to render the full world extents at zoom 1.
