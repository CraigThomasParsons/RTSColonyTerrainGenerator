# SimulateCity - CivicOverreach (v1)

CivicOverreach is a pure analysis + synthesis stage inspired by SimCity 2000.
It generates abandoned civic infrastructure (bridges, roads, buildings)
from heightmap artifacts without running any external simulation engine.

## Inputs
Required (in inbox/):
- heightmap_*.png (16-bit grayscale)
- heightmap.meta.json (min_elevation, max_elevation, sea_level)

Optional inputs are ignored in v1.

## Outputs
- outbox/<job_id>.civic_overreach.worldpayload

## Dependencies
- Python 3
- Pillow (PIL): `pip install pillow`

## Environment overrides
- SIMULATE_CITY_INPUT_DIR (default: MapGenerator/SimulateCity/inbox)
- SIMULATE_CITY_OUTPUT_DIR (default: MapGenerator/SimulateCity/outbox)
- SIMULATE_CITY_ARCHIVE_DIR (default: MapGenerator/SimulateCity/archive)
- SIMULATE_CITY_FAILED_DIR (default: MapGenerator/SimulateCity/failed)
- SIMULATE_CITY_LOG_DIR (default: logs/jobs)

## Install (systemd)
```bash
cd MapGenerator/SimulateCity
./install.sh
```

## Run manually
```bash
cd MapGenerator/SimulateCity
bin/run_civic_overreach.sh <job_id>
```

## Watch heightmap outbox (systemd)
```bash
cd MapGenerator/SimulateCity
bin/consume_simulatecity_job.sh
```

## Tests
```bash
cd MapGenerator/SimulateCity/tests
./run_smoke_test.sh
```

## Notes
- This stage does not block the pipeline and can be removed without breaking contracts.
- Output JSON includes concrete geometry, heuristic rationale, and provenance metadata.
