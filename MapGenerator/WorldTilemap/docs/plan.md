# WorldTilemap — Implementation Plan

## Position in Pipeline

```
... → PATHFINDER → PLAYABLE → WORLDTILEMAP → (PNG output)
```

WorldTilemap is a new stage inserted immediately after Playable. It is the canonical
static-image output of the pipeline — replacing the Playwright-based WorldSnapshot
approach with a direct pygame offscreen renderer using the same corner-based tile
selection as `Algorithms/WorldGeneration/PerlinNoise/world_drawer.py`.

---

## What It Consumes

From `Playable/outbox/`:

| File | Content |
|------|---------|
| `<id>.worldpayload` | Full tile grid — terrain, weather, decorations per tile |
| `<id>.playable.json` | Start zones, resource clusters (wood, stone) |

### Tile structure (worldpayload)

```json
{
  "x": 12, "y": 7,
  "terrain": "grass",
  "weather": { "slope": 420, "flow": 12, "basin": 303564312 },
  "decorations": [
    { "type": "tree", "variety": "oak" }
  ]
}
```

Terrain values: `deep_water`, `water`, `dirt`, `grass`, `rock`, `mountain`

### Resource structure (playable.json)

```json
{
  "start_zones":       [ { "id": "start_1", "x": 43, "y": 80 } ],
  "resource_clusters": [ { "id": "start_1_wood", "type": "wood", "x": 49, "y": 84 },
                         { "id": "start_1_stone", "type": "stone", "x": 52, "y": 81 } ],
  "settlement_labels": [ { "id": "start_1", "type": "start", "x": 43, "y": 80 } ]
}
```

Resource types expected: `wood`, `stone`. Mines may appear as `decoration.type == "mine"`
in the worldpayload or as an additional resource type added to Playable.

---

## What It Produces

`WorldTilemap/outbox/<id>.png` — a pixel-perfect tilemap render of the full world showing:
- Terrain with smooth corner-blended transitions
- Trees, rocks, bushes from tile decorations
- Wood and stone resource cluster markers
- Mine markers
- Player start zone markers

---

## Tileset

**File:** `punyworld-overworld-tileset-perlin.png`
- Dimensions: 432 × 1040 px
- Tile size: 16 × 16 px (27 cols × 65 rows)
- PerlinNoise only uses rows 0–14 (y 0–224) for 7 terrain types × 16 corner variants
- Rows 14–65 (y 224–1040) contain decoration and object sprites — **to be mapped**

### Terrain → Tileset mapping (from PerlinNoise config.py)

| worldpayload `terrain` | Tileset constant | Priority (draw order) |
|------------------------|-----------------|----------------------|
| `deep_water` | `OCEAN3` (0) | 0 — bottom |
| `water` | `OCEAN1` (2) | 2 |
| `dirt` | `BEACH` (3) | 3 |
| `grass` | `GRASS` (4) | 4 |
| `rock` | `MOUNTAIN` (5) | 5 |
| `mountain` | `SNOW` (6) | 6 — top |

`OCEAN2` (1) is unused — `water` maps directly to `OCEAN1`.

### Decoration sprite mapping (to be confirmed by inspecting tileset rows 14–65)

Before implementation, open the tileset image and record the pixel coordinates of:
- Tree sprite (oak / pine)
- Rock / stone sprite
- Mine entrance sprite (or use a coloured overlay if absent)
- Start zone marker (flag / banner, or coloured overlay)

---

## Rendering Algorithm

Straight port of `PerlinNoise/world_drawer.py` with the following additions.

### Pass 1 — Base terrain (corner-based tile selection)

For each tile `(x, y)` where `x < width-1` and `y < height-1`:

1. Sample the four corners of the tile quad:
   ```
   corners = [
       grid[y+1][x+1],   # bottom-right  → bit 0 (weight 1)
       grid[y+1][x],     # bottom-left   → bit 1 (weight 2)
       grid[y][x+1],     # top-right     → bit 2 (weight 4)
       grid[y][x],       # top-left      → bit 3 (weight 8)
   ]
   ```
2. Iterate terrain types from lowest priority to highest.
3. For the first terrain type present in any corner, build the 4-bit index:
   `index = sum(2**i for i, c in enumerate(corners) if c == terrain_type)`
4. Blit `TERRAIN_TILES[terrain_type][index]` (16×16 subsurface) to `(x*16, y*16)`.

Edge tiles (rightmost column, bottom row) blit the all-corners-match variant (index 15).

### Pass 2 — Decorations

For each tile with `decorations[]`:
- `type == "tree"`: blit tree sprite centred on tile
- `type == "rock"`: blit rock sprite centred on tile
- `type == "bush"`: blit bush sprite centred on tile (or skip in v1)
- `type == "mine"`: blit mine sprite centred on tile

### Pass 3 — Resource cluster overlays

For each entry in `resource_clusters`:
- `type == "wood"`: draw a small green circle overlay at `(x*16+8, y*16+8)`, r=6
- `type == "stone"`: draw a small grey circle overlay at `(x*16+8, y*16+8)`, r=6
- `type == "mine"` (if added to Playable): draw a dark red circle overlay

### Pass 4 — Start zone markers

For each entry in `start_zones`:
- Draw a white square border (2px) around the tile at `(x*16, y*16, 16, 16)`
- Optionally blit a flag/banner sprite if one exists in the tileset

---

## Files to Create

```
MapGenerator/WorldTilemap/
├── bin/
│   ├── consume_worldtilemap_job.sh     ← systemd worker (Bash)
│   ├── worldtilemap.py                 ← main engine (Python)
│   ├── renderer.py                     ← TilemapRenderer class (pygame offscreen)
│   └── tileset/
│       ├── punyworld-overworld-tileset-perlin.png   ← copy from Algorithms
│       └── config.py                               ← terrain + sprite constants
├── docs/
│   └── plan.md                         ← this file
├── systemd/
│   ├── worldtilemap.path               ← watches Playable/outbox for .worldpayload
│   └── worldtilemap.service            ← one-shot, runs consume script
├── inbox/
├── outbox/
├── archive/
├── debug/
├── failed/
├── install.sh
└── README.md
```

---

## `bin/renderer.py` — TilemapRenderer

```python
import os
os.environ.setdefault("SDL_VIDEODRIVER", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from pathlib import Path
from tileset.config import ALL_TERRAIN_TYPES, TERRAIN_TILES, TERRAIN_JSON_MAP, TILE_SIZE

class TilemapRenderer:
    def __init__(self, tileset_path: Path):
        pygame.init()
        sheet = pygame.image.load(str(tileset_path)).convert_alpha()
        self.terrain_sprites = self._cut_terrain(sheet)
        self.decoration_sprites = self._cut_decorations(sheet)

    def _cut_terrain(self, sheet):
        # 7 terrain types × 16 corner variants → list of lists of Surfaces
        ...

    def _cut_decorations(self, sheet):
        # keyed by decoration type → Surface
        ...

    def render(self, tiles, width, height, resource_clusters, start_zones) -> pygame.Surface:
        surface = pygame.Surface((width * TILE_SIZE, height * TILE_SIZE))
        grid = self._build_grid(tiles, width, height)
        self._pass_terrain(surface, grid, width, height)
        self._pass_decorations(surface, grid, width, height)
        self._pass_resources(surface, resource_clusters)
        self._pass_starts(surface, start_zones)
        return surface

    def save(self, surface: pygame.Surface, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(output_path))
```

---

## `bin/worldtilemap.py` — Main Engine

Same CLI pattern as `worldsnapshot.py`:

```
--input     Playable outbox directory
--output    WorldTilemap outbox directory
--log-dir   Job log directory root
--job-id    Specific job id (optional)
```

Job selection logic:
1. Scan `Playable/outbox/` for `<id>.worldpayload` files
2. Check `Playable/outbox/<id>.playable.json` exists alongside it
3. Skip any job that already has `WorldTilemap/outbox/<id>.png`
4. Process the oldest unprocessed job

---

## `bin/consume_worldtilemap_job.sh`

Same pattern as other stage consumers:

```bash
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

INPUT_DIR="${WORLD_TILEMAP_INPUT_DIR:-$REPO_ROOT/MapGenerator/Playable/outbox}"
OUTPUT_DIR="${WORLD_TILEMAP_OUTPUT_DIR:-$REPO_ROOT/MapGenerator/WorldTilemap/outbox}"
LOG_DIR="${WORLD_TILEMAP_LOG_DIR:-$REPO_ROOT/logs/jobs}"

python3 "$SCRIPT_DIR/worldtilemap.py" \
  --input  "$INPUT_DIR" \
  --output "$OUTPUT_DIR" \
  --log-dir "$LOG_DIR"
```

---

## Systemd Units

### `worldtilemap.path`

```ini
[Unit]
Description=Watch for new Playable worldpayload jobs

[Path]
PathChanged=<repo>/MapGenerator/Playable/outbox
Unit=worldtilemap.service

[Install]
WantedBy=multi-user.target
```

### `worldtilemap.service`

```ini
[Unit]
Description=WorldTilemap renderer (one-shot)

[Service]
Type=oneshot
EnvironmentFile=-<repo>/.env
ExecStart=<repo>/MapGenerator/WorldTilemap/bin/consume_worldtilemap_job.sh
```

---

## Environment Variables

```bash
WORLD_TILEMAP_INPUT_DIR    # default: MapGenerator/Playable/outbox
WORLD_TILEMAP_OUTPUT_DIR   # default: MapGenerator/WorldTilemap/outbox
WORLD_TILEMAP_LOG_DIR      # default: logs/jobs
```

---

## Dependencies

```
pygame     # offscreen SDL rendering
```

No browser, no Playwright, no display required.

---

## Implementation Steps

1. **Map the tileset** — open `punyworld-overworld-tileset-perlin.png` (432×1040) and
   record pixel coordinates for decoration sprites in rows 14–65 (y > 224). Add them
   to `tileset/config.py`.

2. **Copy tileset** — copy from `Algorithms/Assets/SpriteSheets/PunyWorld/` into
   `WorldTilemap/bin/tileset/`.

3. **Write `tileset/config.py`** — terrain constants, `TERRAIN_JSON_MAP` dict, `TERRAIN_TILES`
   coordinate tables (straight copy from PerlinNoise config.py), plus new
   `DECORATION_TILES` and `RESOURCE_COLOURS` for pass 2–4.

4. **Write `renderer.py`** — `TilemapRenderer` class with the four rendering passes.

5. **Write `worldtilemap.py`** — job selection, JSON loading, dispatch to renderer, logging.

6. **Write `consume_worldtilemap_job.sh`** — thin Bash wrapper matching existing stage
   consumer pattern.

7. **Write systemd units** — `.path` watching Playable outbox, `.service` one-shot.

8. **Write `install.sh`** — `pip install pygame`, copy tileset, enable systemd units.

9. **Test** — run against an existing Playable outbox artefact:
   ```bash
   python3 bin/worldtilemap.py \
     --input  ../../Playable/outbox \
     --output ./outbox \
     --log-dir /tmp/logs
   ```

---

## Mines — Open Question

The pipeline currently produces mines via:
- `WorldFeatures` (cave/mine openings in terrain features)
- `CivicOverreach` (abandoned civic structures)

Neither currently writes a `mine` entry into the worldpayload decorations or playable.json
resource_clusters. **Resolution options:**
- A. Add `"type": "mine"` to `resource_clusters` in Playable (needs Playable update)
- B. Read CivicOverreach output directly if it writes to a known path
- C. Infer mine locations from `rock` terrain + high `weather.slope` as a heuristic in WorldTilemap itself (no upstream changes needed for v1)

Recommend **option C for v1** — mark any `rock` tile with slope > 8000 as a probable mine
site with a visual indicator, then revisit once Playable or CivicOverreach formally
produces mine records.

---

## Out of Scope (v1)

- Routes / pathfinder overlay (golden lines) — can be added as pass 5 later
- Animated output
- Multiple zoom levels
- Replacing WorldPreview (the interactive HTML viewer stays)
- Replacing WorldSnapshot (Playwright mode stays for now; WorldTilemap is additive)
