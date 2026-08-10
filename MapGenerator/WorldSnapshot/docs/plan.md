# WorldSnapshot — Tilemap Renderer Implementation Plan

> **Superseded.** The tilemap renderer has been moved to a dedicated new stage:
> `MapGenerator/WorldTilemap/` — see `WorldTilemap/docs/plan.md`.
> WorldSnapshot itself remains unchanged (Playwright mode only).

## Goal

Add a second rendering mode to WorldSnapshot that produces a PNG using a **pure
Python tilemap renderer** — the same corner-based tile-selection approach used in
`Algorithms/WorldGeneration/PerlinNoise/world_drawer.py` — instead of launching a
headless browser via Playwright.

This mode reads `world.json` directly from the WorldPreview outbox directory (same
pipeline dependency, no extra stages), renders it offline with **pygame in offscreen
mode**, and saves the PNG with `pygame.image.save`.

The existing Playwright mode is untouched. The new mode is selected via `--mode tilemap`.

---

## Why

| | Playwright mode | Tilemap mode |
|---|---|---|
| **Dependency** | Chromium + Playwright | pygame + Pillow |
| **Speed** | ~3–5 s browser launch | < 1 s |
| **Fragility** | Browser, canvas JS, timing waits | Pure Python, no DOM |
| **Visual style** | WorldPreview JS renderer (32×32 atlas) | PerlinNoise corner-tile style (16×16 punyworld) |
| **Headless** | Requires X or virtual framebuffer | SDL offscreen driver — no display needed |
| **Use case** | Faithful to interactive viewer | Fast, lightweight, CI-friendly |

---

## How the PerlinNoise Renderer Works (reference)

Source: `Algorithms/WorldGeneration/PerlinNoise/world_drawer.py`

The key algorithm is **corner-based tile selection**:

1. For each tile at `(x, y)`, sample the terrain type of its four corners:
   - top-left `(x, y)`, top-right `(x+1, y)`, bottom-left `(x, y+1)`, bottom-right `(x+1, y+1)`
2. Find the *lowest-priority* terrain type present in those corners (priority = visual layering order)
3. For each terrain type present, build a 4-bit index where each bit represents whether
   that corner matches the terrain type: `index += 2**power` for each matching corner
4. Use the index (0–15) to pick one of 16 pre-cut sprite variants from the tileset
5. Blit the sprite to the surface

This produces smooth blended transitions at terrain boundaries — the same visual style as
the classic PunyWorld overworld tileset.

---

## Terrain Mapping

PathFinder JSON terrain values → PerlinNoise terrain constants:

| JSON `terrain` | Tilemap constant | Visual |
|----------------|-----------------|--------|
| `deep_water` | `OCEAN3` | Deep ocean |
| `water` | `OCEAN1` | Shallow water |
| `dirt` | `BEACH` | Sand/shore |
| `grass` | `GRASS` | Grassland |
| `rock` | `MOUNTAIN` | Rocky highland |
| `mountain` | `SNOW` | Mountain peak |

The punyworld tileset already has 16 corner-variants for each of these types.

---

## Files to Create / Modify

### New: `bin/tilemap_renderer.py`

A self-contained module. No pygame window is opened — uses SDL offscreen driver.

```
class TilemapRenderer:
    __init__(tileset_path, tile_size, terrain_tiles_config)
        - os.environ['SDL_VIDEODRIVER'] = 'offscreen'
        - pygame.init()
        - load tileset, cut 16 subsurfaces per terrain type

    render(tiles: list[dict], map_width: int, map_height: int) -> pygame.Surface
        - build 2D grid from flat tiles list
        - for each (x, y): corner-based tile selection → blit sprite

    save(surface, output_path: Path)
        - pygame.image.save(surface, str(output_path))
```

### New: `bin/tileset/`

Bundle a copy of the punyworld overworld tileset (the perlin-noise variant):

```
bin/tileset/punyworld-overworld-tileset-perlin.png   ← copy from Algorithms repo
bin/tileset/config.py                                ← terrain type constants + sprite coords
```

`config.py` is adapted from `Algorithms/WorldGeneration/PerlinNoise/config.py` — same
tile coordinate tables, same `TERRAIN_TILES` mapping, same terrain type constants.

### Modified: `bin/worldsnapshot.py`

Add `--mode` argument (default `playwright`):

```python
parser.add_argument(
    "--mode",
    choices=["playwright", "tilemap"],
    default="playwright",
    help="Rendering backend",
)
```

Add `render_tilemap_snapshot(job, log_file)` function:

```python
def render_tilemap_snapshot(job: JobSelection, log_file: Path) -> int:
    world_json = job.input_dir / "world.json"
    # load JSON, extract tiles + map dimensions
    # instantiate TilemapRenderer
    # call render() → surface
    # call save() → job.output_path
    # log result
```

Dispatch in `main()`:

```python
if args.mode == "tilemap":
    return render_tilemap_snapshot(job, log_file)
else:
    return render_snapshot(job, log_file, args.timeout)
```

### Modified: `bin/consume_worldsnapshot_job.sh`

Add optional `WORLD_SNAPSHOT_MODE` env var (default `playwright`):

```bash
--mode "${WORLD_SNAPSHOT_MODE:-playwright}"
```

### Modified: `install.sh`

Add `pygame` to pip install step alongside any existing dependencies.

---

## Implementation Steps

### Step 1 — Bundle the tileset and config

- Copy `punyworld-overworld-tileset-perlin.png` from the Algorithms repo into
  `MapGenerator/WorldSnapshot/bin/tileset/`
- Create `bin/tileset/config.py` with the terrain type constants, `ALL_TERRAIN_TYPES`,
  and `TERRAIN_TILES` sprite coordinate tables (straight copy from PerlinNoise `config.py`,
  minus the window/world-size constants which are not needed here)

### Step 2 — Write `bin/tilemap_renderer.py`

Key implementation details:

```python
import os
os.environ.setdefault("SDL_VIDEODRIVER", "offscreen")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

TILE_SIZE = 16  # punyworld tileset uses 16×16 sprites

TERRAIN_ORDER = ["deep_water", "water", "dirt", "grass", "rock", "mountain"]
# lowest index = lowest draw priority (drawn underneath others)
```

Corner sampling:
```python
def _corner_types(self, grid, x, y):
    # grid[y][x] = terrain string
    # returns [bottom_right, bottom_left, top_right, top_left]
    return [
        grid[y + 1][x + 1],
        grid[y + 1][x],
        grid[y][x + 1],
        grid[y][x],
    ]
```

Tile index:
```python
def _tile_index(self, corners, terrain_type):
    index = 0
    for power, corner in enumerate(corners):
        if corner == terrain_type:
            index += 2 ** power
    return index  # 0–15
```

Surface size: `map_width * TILE_SIZE` × `map_height * TILE_SIZE` pixels.

Boundary handling: skip tiles where `x == map_width - 1` or `y == map_height - 1`
(corners would read out of bounds), filling edge pixels with the tile's own terrain sprite
(index 15, all-corners-match).

### Step 3 — Integrate into `worldsnapshot.py`

- Add `--mode` argument
- `render_tilemap_snapshot` reads `world.json`, builds the flat tile list into a 2D grid,
  delegates to `TilemapRenderer`, logs timing
- Fall back to Playwright if `world.json` is missing but `index.html` exists

### Step 4 — Wire mode into the shell consumer

```bash
WORLD_SNAPSHOT_MODE="${WORLD_SNAPSHOT_MODE:-playwright}"
```

Operators can switch mode by setting the env var in the systemd drop-in or `.env` file.

### Step 5 — Test

```bash
# Playwright mode (existing, unchanged)
python bin/worldsnapshot.py \
  --input MapGenerator/WorldPreview/outbox \
  --output /tmp/test_out \
  --log-dir /tmp/test_logs \
  --mode playwright

# Tilemap mode (new)
python bin/worldsnapshot.py \
  --input MapGenerator/WorldPreview/outbox \
  --output /tmp/test_out \
  --log-dir /tmp/test_logs \
  --mode tilemap
```

Compare outputs visually. The tilemap render will be smaller in pixel dimensions
(16 px/tile vs 32 px/tile) but should show the same terrain layout.

---

## File Layout After Implementation

```
MapGenerator/WorldSnapshot/
├── bin/
│   ├── consume_worldsnapshot_job.sh     (modified: add --mode)
│   ├── worldsnapshot.py                 (modified: add --mode, render_tilemap_snapshot)
│   ├── tilemap_renderer.py              (new)
│   └── tileset/
│       ├── punyworld-overworld-tileset-perlin.png  (new, copied from Algorithms)
│       └── config.py                               (new, adapted from PerlinNoise)
├── docs/
│   ├── pipeline_analysis.md
│   └── plan.md
├── systemd/
│   ├── worldsnapshot.path
│   └── worldsnapshot.service
├── inbox/
├── outbox/
├── install.sh                           (modified: pip install pygame)
└── README.md
```

---

## Dependencies

```
playwright      # existing — for playwright mode
pygame          # new — for tilemap mode
```

Both can coexist. If `pygame` is not installed, the tilemap mode fails fast with a clear
error; the playwright mode is unaffected.

---

## Out of Scope

- Decorations / tree rendering (can be added in a follow-up; PerlinNoise doesn't render
  decorations either — they're a WorldPreview-only feature)
- Route overlays (golden lines from PathFinder routes[])
- Scaling / zoom options (the output will be `map_width × 16` × `map_height × 16` pixels)
- Replacing the Playwright mode — both modes remain available
