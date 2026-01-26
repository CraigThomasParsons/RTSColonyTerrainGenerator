# Playable

Playable is a pipeline stage that prepares world payloads for RTS gameplay by
identifying start zones, placing resource clusters, and labeling expansion
areas. This scaffolding currently performs a deterministic pass-through copy and
emits placeholder labels, so downstream exporters can be wired immediately.

## Inputs
- World payloads from WorldFeatures (default)
- Optional: InfrastructureBuilder output (if configured via env)

## Outputs
- outbox/<job_id>.worldpayload (copied from input)
- outbox/<job_id>.playable.json (placeholder labels)

## Determinism
- No randomness; output is derived directly from input job order.
- Placeholder labels are deterministic and tagged with job_id.

## Environment overrides
- PLAYABLE_INPUT_DIR (default: MapGenerator/WorldFeatures/outbox)
- PLAYABLE_OUTPUT_DIR (default: MapGenerator/Playable/outbox)
- PLAYABLE_LOG_DIR (default: logs/jobs)

## Run manually
```bash
cd MapGenerator/Playable
bin/consume_playable_job.sh
```

## Install (systemd)
```bash
cd MapGenerator/Playable
./install.sh
```

## TODO (implementation)
- Select start zones using slope + accessibility + distance to resources
- Place wood + ore clusters within a fixed radius per start zone
- Label expansions based on path cost tiers
- Emit labels into payload metadata (not just sidecar JSON)
