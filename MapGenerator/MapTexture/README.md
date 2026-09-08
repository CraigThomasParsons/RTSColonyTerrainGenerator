# MapTexture

MapTexture is an optional, terminal presentation stage after Playable. It uses
the deterministic heightmap and completed gameplay artifacts to create texture
controls and offline background candidates. Its pixels are never gameplay
authority and never flow back into map generation, pathfinding, or exports.

V1 is deliberately offline. The only provider is `offline-deterministic`; it
has no token, HTTP, or paid-submission path. Map Mosaic was inspected only as
prior art (upstream commit `d50802e569ae32ef02b7eacf7ba177b8f9f8dd32`,
GPL-3.0). No Map Mosaic source, prompt, test, or UI code is used here.

## Contract

Inputs are the job's binary `.heightmap`, deterministic heightmap PNG,
Playable `.worldpayload`, and `.playable.json`. Strict dimension, dense-tile,
and job-id agreement is required.

Each run writes 128×128 semantic, protected, topology, and decoration controls,
a versioned visual brief and run plan, and one to four deterministic 512×512
candidates. Every authoritative tile owns exactly one 4×4 output region.

Candidates receive generation provenance and structural validation. Automation
may reject but cannot approve. `approve` requires a human actor and reason and
atomically publishes exactly one `background.png`; authoritative overlays are
rendered later by Map Studio.

```bash
python3 MapGenerator/MapTexture/bin/maptexture.py run \
  --heightmap MapGenerator/Heightmap/outbox/<id>.heightmap \
  --heightmap-png MapGenerator/SimulateCity/inbox/<id>/heightmap_<id>.png \
  --worldpayload MapGenerator/Playable/outbox/<id>.worldpayload \
  --playable MapGenerator/Playable/outbox/<id>.playable.json \
  --output MapGenerator/MapTexture/outbox/<id>

python3 MapGenerator/MapTexture/bin/maptexture.py approve \
  --output MapGenerator/MapTexture/outbox/<id> --candidate 0 \
  --actor Craig --reason "Compared in Map Studio"
```

Run the credit-free tests with:

```bash
python3 -m unittest discover MapGenerator/MapTexture/tests
```
