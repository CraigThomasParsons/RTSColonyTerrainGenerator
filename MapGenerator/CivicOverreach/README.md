# CivicOverreach (Phase 1)

CivicOverreach creates abandoned civic structures (bridges, roads, buildings)
from heightmap artifacts using rule-based, SimCity-inspired heuristics.

## What this stage does
- Consumes heightmap PNG + meta
- Synthesizes ruined infrastructure
- Emits a single worldpayload JSON

## What this stage does NOT do
- It does NOT run OpenSC2K or any game engine
- It does NOT simulate population, economy, or power
- It does NOT require determinism

## Phase 2 (Reserved)
Phase 2 will replace internal logic with headless simulation and probes
while preserving the output schema.

## Usage
```bash
cd MapGenerator/CivicOverreach
bin/run_civic_overreach.sh <job_id>
```
