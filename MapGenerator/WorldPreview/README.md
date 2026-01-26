# WorldPreview

Human-facing inspection stage. Consumes a world payload (e.g., PathFinder output) and emits static, deterministic artifacts suitable for offline inspection via `file://`.

## Input
- World payload JSON placed in `inbox/` or received from the upstream PathFinder outbox.

## Output (per job)
```
outbox/<job_id>/
├── index.html
├── style.css
├── main.js
├── world.json
├── assets/
│   ├── tileset.png
│   ├── colormap.png
│   └── legend.png
└── README.md
```
- `world.json`: copied from input payload (pretty-printed).
- `index.html`: embeds the world data inline for `file://` usage.
- `style.css` / `main.js`: vanilla JS viewer with zoom/pan, layer toggles, hover inspect.
- `assets/tileset.png`: generated symbolic tiles for ridges, vegetation, shorelines, ramps/features, and roads.
- `assets/colormap.png`, `assets/legend.png`: optional helpers for inspection.

## Running
- Build: `cd MapGenerator/WorldPreview && ./install.sh`
- Manual run: `bin/consume_worldpreview_job.sh`
- Systemd:
  - `cd MapGenerator/WorldPreview/systemd && ./install.sh`
  - Ensure: `systemctl --user daemon-reload && systemctl --user enable --now worldpreview.path`

## UI Features
- Top-down canvas renderer (no server required).
- Layer toggles: heightmap, terrain tiles, features, paths/roads.
- Zoom/pan with mouse wheel + drag.
- Hover inspection: coordinates, height value, tile type, feature metadata.
- Uses generated tileset for ridges, trees/vegetation, shorelines, ramps/features, and roads.

## Determinism
- Assets and layout are generated deterministically from the input payload filename (job ID). No runtime randomness in JS rendering.
