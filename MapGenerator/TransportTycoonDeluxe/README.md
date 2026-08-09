# TransportTycoonDeluxe

OpenTTD-backed stage for transport simulation scaffolding.
This stage now accepts heightmap inputs and emits a confirmation artifact after map generation.

## Inputs
- inbox/<job_id>.heightmap.png (16-bit grayscale heightmap)

## Outputs
- outbox/<job_id>.transporttycoon.json (map generation confirmation)

## Environment overrides
- TRANSPORT_TYCOON_DELUXE_INPUT_DIR (default: MapGenerator/TransportTycoonDeluxe/inbox)
- TRANSPORT_TYCOON_DELUXE_OUTPUT_DIR (default: MapGenerator/TransportTycoonDeluxe/outbox)
- TRANSPORT_TYCOON_DELUXE_ARCHIVE_DIR (default: MapGenerator/TransportTycoonDeluxe/archive)
- TRANSPORT_TYCOON_DELUXE_FAILED_DIR (default: MapGenerator/TransportTycoonDeluxe/failed)
- TRANSPORT_TYCOON_DELUXE_DEBUG_DIR (default: MapGenerator/TransportTycoonDeluxe/debug)
- TRANSPORT_TYCOON_DELUXE_TEMP_DIR (default: MapGenerator/TransportTycoonDeluxe/debug)
- TRANSPORT_TYCOON_DELUXE_SEED (default: derived from job id)
- TRANSPORT_TYCOON_DELUXE_MAP_SIZE (default: 1024x1024)
- TRANSPORT_TYCOON_DELUXE_MAP_X_EXP (default: 10)
- TRANSPORT_TYCOON_DELUXE_MAP_Y_EXP (default: 10)
- TRANSPORT_TYCOON_DELUXE_WATER_LEVEL (default: 2)
- TRANSPORT_TYCOON_DELUXE_RUN_SECONDS (default: 5)

## Install (systemd)
```bash
cd MapGenerator/TransportTycoonDeluxe
./install.sh
```

## Run manually
```bash
cd MapGenerator/TransportTycoonDeluxe
bin/run_transport_tycoon.sh
```

## Notes
- Infrastructure extraction is intentionally not implemented yet.
- This is a proof-of-life stage to validate OpenTTD headless generation.
