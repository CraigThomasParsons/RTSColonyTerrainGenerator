# Artifact Format Catalogue (Baseline)

The on-disk format of each artifact type, from its authoritative reader/writer. Multi-byte
binary fields are little-endian unless noted.

## `.heightmap` — binary (Heightmap engine)

Writer: `Heightmap/heightmap-engine/src/main.rs`. Layout (`N = width*height`):

```
u32  map_width_in_cells
u32  map_height_in_cells
u64  deterministic_seed        (hash of job_id + dims; the API supplies no seed)
u8[N]  height values           (row-major, normalized 0..255)
u8[N]  terrain layer values    (row-major; 0=Water 1=Land 2=PineMountain 3=RockMountain)
```

Total = `16 + 2N` bytes. Confirmed by `Tiler/IO/HeightmapReader.cs` (terrain validated 0..3).

## `.weather` — binary (WeatherAnalyses)

Writer: `WeatherAnalyses/src/weather_map.rs`.

```
u32  magic   = 0x57414E41  ("WANA")
u16  version = 1
u32  width
u32  height
u16  layer_count = 3
i16[N] slope     (layer 1)
u8[N]  flow      (layer 2)
u32[N] basin     (layer 3)
```

## `.maptiles` — binary (Tiler)

Writer: `Tiler/IO/MapTilesWriter.cs`. 32-byte header + body:

```
char[4] magic            ("MTIL")
u32     version          (1)
u32     tile_width
u32     tile_height
u64     deterministic_seed
u32     tile_count
u32     reserved         (0)
u16[tile_count] tile_ids (row-major)
```

Tile dimensions are twice the cell dimensions per axis (a 64×64-cell map → 128×128 tiles),
which is the cell-to-tile expansion Epic 1 (M3) formalizes and verifies.

## `.worldpayload` — text / JSON, a single file

Writer: `TreePlanter/src/World/WorldPayloadWriter.php` (pretty-printed JSON). Augmented
in place by WorldFeatures; copied by Playable.

```json
{
  "version": 1,
  "job_id": "<id>",
  "map": { "width_in_cells": W, "height_in_cells": H },
  "tiles": [
    { "x": 12, "y": 7, "terrain": "grass",
      "weather": { "slope": 420, "flow": 12, "basin": 303564312 },
      "decorations": [ { "type": "tree", "variety": "oak" } ] }
  ]
}
```

Terrain values seen: `deep_water, water, dirt, grass, rock, mountain`. WorldFeatures adds a
`features` array. Consumers parse leniently (`ignoreUnknownKeys = true`), so the schema is
loosely versioned.

## `.playable.json` — text / JSON (Playable)

Writer: `Playable/bin/playable.py` (`PASSABLE_TERRAINS`, `SLOPE_THRESHOLD=6000`,
`MIN_START_SEPARATION=24`).

```json
{ "start_zones":       [ { "id": "start_1", "x": 43, "y": 80 } ],
  "resource_clusters": [ { "id": "start_1_wood", "type": "wood", "x": 49, "y": 84 } ],
  "settlement_labels": [ { "id": "start_1", "type": "start", "x": 43, "y": 80 } ] }
```

## PathFinder `<id>.json` (ConnectivityReport) — text / JSON

Writer: `PathFinder/…/PathFinderApp.kt`. Re-serializes `jobId, map, tiles, features,
routes[], requests[]` — hence multi-MB (it re-embeds the whole tile grid).
`routes[] = {from,to,success,cost,pathLength,path[]}`; `requests[] = {type,x,y,reason}`.

## `.wcar` — binary chunked container (CartridgeManufacturer)

Source: `bin/wcar-tools/crates/wcar/src/{lib.rs,format.rs}`. `HEAD` chunk carries magic
`b"WCAR"` + version; then a tag stream (4-byte tag + u32 length + data):
`HEAD, SEED, PROV, HMAP, TILE, BIOM, FEAT, PATH, NAVI, CHK0, EXTX`.

## `.chk` / `.scm` — StarCraft binary (MPQ)

Written by StargusExport (`stargus-exporter`, Python `struct`+`zlib`) and by
CartridgeManufacturer (`wcar_export_chk`). The wrapper validates `.scm`: ≥ 10240 bytes and a
4-byte MPQ signature `4d 50 51 1a` (`MPQ\x1a`).

## `.png`

WorldSnapshot: Playwright full-page screenshot of WorldPreview `index.html`. Heightmap's
`export_heightmap_png.py` also writes a 16-bit `heightmap_<id>.png` (pixel = height*257) +
`heightmap.meta.json` into SimulateCity's inbox.

---

## Baseline hazards

Behaviours to preserve-and-characterize, not silently "fix". Each is a candidate for a
specification-correction ADR (which requires human review per `AGENTS.md`).

1. **WeatherAnalyses misreads the `.heightmap` body.** `WeatherAnalyses/src/heightmap.rs`
   treats the body as `width*height` **i16** values (`expected = w*h*2`), whereas the format
   is `u8[N]` heights followed by `u8[N]` terrain. It consumes the correct *byte count*
   (`16 + 2N`) but reinterprets height+terrain bytes as signed 16-bit heights, so every
   downstream weather layer is computed from a misread grid. **The golden `.weather`
   artifacts encode this behaviour** — a faithful reimplementation must reproduce it, or the
   change must be an approved specification correction.

2. **`.worldpayload` is a file, not a directory.** `MapGenerator/stages.md` repeatedly
   describes `<id>.worldpayload/` as a directory of heightmap/maptiles/weather/manifest. On
   disk it is a single multi-MB JSON file. `stages.md` is unreliable; the code is the source
   of truth (it even self-flags "### This diagram is wrong").

3. **Three heightmap readers disagree.** `Tiler/IO/HeightmapReader.cs` is correct;
   `export_heightmap_png.py` reads only the first `N` height bytes (fine for PNG);
   `WeatherAnalyses/src/heightmap.rs` misreads as above. A shared, verified heightmap reader
   is a natural early migration target (Phase 5 / M6).

4. **mapgenctl tracks only 4 of 17 stages.** `PIPELINE_STAGES = heightmap, tiler, weather,
   treeplanter`; the other stages have no completion tracking in the CLI. `--until` only
   understands those four.

5. **Placeholder engines.** AncientCivilization emits `json!([…])` literals with a hardcoded
   `collapse_reason = "none"`; TransportTycoonDeluxe writes `"Infrastructure extraction not
   implemented yet"`. Real binaries, placeholder output.
