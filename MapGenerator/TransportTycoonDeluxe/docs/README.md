# TransportTycoonDeluxe Stage (v1)

## What this stage does
- Consumes exactly one heightmap input: `inbox/<job_id>.heightmap.png`.
- Launches OpenTTD headlessly with a deterministic seed and fixed settings.
- Generates a world from the provided heightmap.
- Emits a confirmation artifact: `outbox/<job_id>.transporttycoon.json`.

## What this stage does NOT do yet
- No infrastructure extraction (roads, rails, industries, stations).
- No AI logic or gameplay simulation.
- No savegame parsing.
- No long-running daemon process.

## How it evolves in future versions
- Capture OpenTTD-generated infrastructure and export structured artifacts.
- Add scenario parameters and template overlays (town placement, climate, industries).
- Support richer outputs such as tile graphs, route suggestions, and economy data.
- Integrate savegame parsing and validation.

## Notes
- This is a proof-of-life stage. It uses a short headless run to allow OpenTTD to initialize the world.
- Configuration is derived from `openttd.cfg.template` and per-run overrides.
