# WorldSnapshot — Pipeline Analysis

## What WorldSnapshot Does

WorldSnapshot is the final visualisation stage of the terrain generation pipeline. It takes
the interactive HTML viewer produced by WorldPreview and renders it into a static PNG image
suitable for reports, CI artefacts, or quick human review.

Currently it does this using **Playwright** (headless Chromium): load the HTML, wait for the
canvas to paint, screenshot it, save the PNG.

---

## Full Pipeline Order

```
[Job Spec JSON]
      │  map_width, map_height, seed
      ↓
 HEIGHTMAP (Rust)
      │  binary heightmap — 1 byte per cell, row-major
      │  outbox/<id>.heightmap
      ├──────────────────────────────┐
      ↓                              ↓
 TILER (Rust)             WEATHERANALYSES (Java)
 classify height →         slope, flow, basin per cell
 terrain types             outbox/<id>.weather
 outbox/<id>.maptiles
      │                              │
      └──────────┬───────────────────┘
                 ↓
          TREEPLANTER (PHP)
          first unified JSON world payload
          tiles: [ {x, y, terrain, weather, decorations} ]
          outbox/<id>.worldpayload
                 │
                 ↓
          WORLDFEATURES (Java/Kotlin)
          add natural features: caves, ramps, river hints
          outbox/<id>.worldpayload  (augmented)
                 │
                 ↓
           PATHFINDER (Java/Kotlin)
           simulate trade routes, evaluate passability
           add routes[] connectivity graph
           outbox/<id>.json
                 │
        ┌────────┼────────────────────┐
        ↓        ↓                    ↓
    PLAYABLE  STARGUS           WORLDPREVIEW (Rust)
    start     EXPORT            generates static HTML viewer
    zones,                      outbox/<id>/
    resource                      index.html
    clusters                      world.json
                                  style.css / main.js
                                  assets/tileset.png
                                        │
                                        ↓
                                 WORLDSNAPSHOT (Python)
                                 renders HTML → PNG
                                 outbox/<id>.png
```

---

## What WorldSnapshot Consumes

WorldSnapshot watches `WorldPreview/outbox/` for directories containing `index.html`.

```
WorldPreview/outbox/<job_id>/
├── index.html          ← WorldSnapshot loads this in headless Chromium
├── world.json          ← copy of the PathFinder JSON (also useful for tilemap renderer)
├── style.css
├── main.js
└── assets/
    └── tileset.png     ← 512×256 atlas, 32×32 sprites, 16 cols × 8 rows
```

The HTML embeds the full world payload inline as `window.WORLD_DATA` to avoid
CORS issues on the `file://` protocol.

### world.json tile structure

Each tile in `world.json` (and in `window.WORLD_DATA.tiles`) looks like:

```json
{
  "x": 12,
  "y": 7,
  "terrain": "grass",
  "weather": {
    "x": 12,
    "y": 7,
    "slope": 420,
    "flow": 12,
    "basin": 303564312
  },
  "decorations": [
    { "type": "tree", "variety": "oak" }
  ]
}
```

**Terrain values:** `deep_water`, `water`, `grass`, `dirt`, `rock`, `mountain`

---

## How the Existing Playwright Renderer Works

`bin/worldsnapshot.py` (`render_snapshot` function):

1. Find the newest WorldPreview job dir that has no corresponding PNG yet
2. Launch headless Chromium via Playwright
3. Navigate to `index.html` via `file://` URI
4. Wait for `#world-canvas` to exist
5. Wait for `#status` text to start with `"Loaded"`
6. Evaluate JS to compute canvas dimensions from `window.WORLD_DATA.tiles` (max X/Y × 32)
7. Set viewport to that exact size
8. Hide `#ui-layer`, normalise camera to zoom=1, trigger a redraw
9. Call `page.screenshot(full_page=True)` → save to `outbox/<id>.png`

### WorldPreview Canvas Rendering (main.js — 3-pass system)

The HTML viewer renders in three passes over the tile grid:

| Pass | What it draws |
|------|--------------|
| Base terrain | Grass, dirt, water, rock — 32×32 sprites from atlas |
| Ridges/cliffs | Elevation differences > 0.15 trigger directional cliff tiles (N/S/E/W) |
| Features | `decorations[]` (trees, rocks, bushes), `routes[]` as golden lines |

---

## Upstream Stage Artefacts

| Stage | Output file | Format | Typical size |
|-------|-------------|--------|--------------|
| Heightmap | `<id>.heightmap` | Binary, 1 byte/cell | 4 KB (64×64) |
| WeatherAnalyses | `<id>.weather` | JSON per-tile | ~5 MB |
| Tiler | `<id>.maptiles` | JSON terrain grid | ~5 MB |
| TreePlanter | `<id>.worldpayload` | JSON world payload | ~5 MB |
| WorldFeatures | `<id>.worldpayload` | JSON world payload (augmented) | ~4.6 MB |
| PathFinder | `<id>.json` | JSON tiles + routes | ~4.7 MB |
| WorldPreview | `<id>/index.html` + assets | HTML + JS + PNG atlas | ~500 KB dir |
| **WorldSnapshot** | **`<id>.png`** | **PNG screenshot** | **~170–220 KB** |

---

## Environment Variables

```bash
WORLD_SNAPSHOT_INPUT_DIR        # default: MapGenerator/WorldPreview/outbox
WORLD_SNAPSHOT_OUTPUT_DIR       # default: MapGenerator/WorldSnapshot/outbox
WORLD_SNAPSHOT_LOG_DIR          # default: logs/jobs
WORLD_SNAPSHOT_TIMEOUT_SECONDS  # default: 20
```

---

## Systemd Trigger

- `.path` unit watches `WorldPreview/outbox/` for new `index.html` files
- `.service` unit runs `consume_worldsnapshot_job.sh` as a one-shot
- The shell script calls `worldsnapshot.py` with the env-var paths

---

## Dependency Chain (condensed)

```
WorldSnapshot
  └─ WorldPreview/outbox/<id>/index.html + world.json
       └─ PathFinder/outbox/<id>.json
            └─ WorldFeatures/outbox/<id>.worldpayload
                 └─ TreePlanter/outbox/<id>.worldpayload
                      ├─ Heightmap/outbox/<id>.heightmap
                      ├─ WeatherAnalyses/outbox/<id>.weather
                      └─ Tiler/outbox/<id>.maptiles
```

---

## Key Technical Notes

- **Determinism:** same seed → same binary heightmap → same everything downstream → pixel-identical PNG
- **File protocol:** WorldPreview embeds JSON inline in HTML so Playwright can load it via `file://`
- **No server required:** the entire pipeline runs locally via systemd path/service units
- **Job isolation:** each job lives in its own UUID-named directory; stages never share mutable state
