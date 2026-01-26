# Ancient Civilization Stage

Purpose: Simulate remnants of a failed proto-civilization to inform player settlement without NPCs or long-run simulation.

- Deterministic
- Consumes explicit upstream artifacts
- Produces machine-readable outputs
- Runs fast (scoring + simple synthesis)
- No agents, no economic timesteps

## Inputs (data files)
- Heightmap: elevation, slope (per tile)
- Water: rivers, lakes, flood plains (risk indices)
- Climate: severity indices (cold/heat/wind/rain), variability
- Resources: density maps (stone, trees, ore)
- PathFinder output: preferred travel routes (polyline paths + costs)
- World payload: base tile grid for contextual checks (optional)

## Core Responsibilities
1. Identify candidate proto-settlement locations via scoring (no agents)
2. Synthesize minimal infrastructure:
   - Settlement centers with footprints
   - Connecting ancient paths (to resources and between settlements)
   - Nearby extraction zones (stone, wood, ore)
3. Simulate collapse:
   - Choose 1–2 causes (climate shift, flooding, overextension)
   - Assign abandonment stages & decay levels
4. Emit artifacts:
   - Ruins (foundations, walls)
   - Ancient paths (movement bonus hints)
   - Cleared, flattened terrain patches
   - Reclaimable resources (early-game caches)

## Internal Model (Deterministic)
- Seed: `hash(job_id + "AncientCivilization")` used only to break ties deterministically.
- Grid: operate on tile coordinates `(x,y)`.
- No stateful sim; pure functions over inputs.

### Settlement Scoring
Score each tile `t` as a candidate center using weighted terms. Let:
- `S(t)`: slope score (prefer moderate slopes: not flat swamp, not steep ridge)
- `W(t)`: water proximity score (prefer near fresh water but avoid flood risk)
- `C(t)`: climate score (prefer mild severity, stable variability)
- `R(t)`: resource proximity score (within `r=12` tiles to mixed resources)
- `A(t)`: accessibility score (near PathFinder preferred routes)
- `E(t)`: elevation band suitability (avoid very low basins + extreme peaks)

Weights (tunable, deterministic constants):
- `α=0.25` (slope), `β=0.20` (water), `γ=0.15` (climate), `δ=0.20` (resources), `ε=0.15` (accessibility), `ζ=0.05` (elevation band)

Normalization (each term scaled to [0,1]):
- `S(t) = 1 - |slope(t) - s_opt| / s_opt` where `s_opt=6` (gentle)
- `W(t) = clamp( prox_freshwater(t,8) - flood_risk(t), 0, 1 )`
- `C(t) = 1 - severity_index(t)` (milder is better)
- `R(t) = mix_density(t, radius=12)` normalized
- `A(t) = clamp( 1 - dist_to_nearest_pf_route(t)/24, 0, 1 )`
- `E(t) = gaussian_band(elevation(t); μ_band, σ_band)` with `μ_band` mid-altitude

Total score:
`Score(t) = αS + βW + γC + δR + εA + ζE`

Select top `K ∈ [1..3]` centers subject to:
- Min distance between centers: `≥ 48` tiles
- Exclude tiles with `flood_risk > 0.6` or `slope > 18`
- Tie-break deterministically by seed hash

### Infrastructure Synthesis
For each center `s`:
- Footprint radius `rf`: `16` tiles; define bounds and orientation by local slope vector
- Extraction zones:
  - Stone: nearest high-density stone cluster within `24` tiles
  - Lumber: nearest stable grass + tree density cluster within `24` tiles
  - Ore: nearest moderate ore density within `36` tiles
- Ancient paths:
  - Connect `s → each extraction zone` via shortest PathFinder-preferred corridor
  - Connect `s → nearest other center` (if any) with a polyline; prefer gentle terrain
- Cleared patches:
  - Within footprint, mark `clear_level ∈ {light, medium, heavy}` based on score quartiles

### Minimal Collapse Model
Pick 1–2 failure causes deterministically from data signals:
- `climate_shift` if `severity_index_avg > 0.55` or variability `> 0.4`
- `flooding` if `flood_risk_avg(center_footprint) > 0.5`
- `overextension` if `avg_path_cost(center→zones) > 900`
- `resource_exhaustion` if `mix_density_avg(center_footprint) < 0.25`

Abandonment stages:
- `early` (few ruins, paths intact) if 0–1 causes, low severity
- `mid` (foundations, partial walls, path decay) if 1–2 causes, medium severity
- `late` (collapsed walls, heavy overgrowth) if ≥2 causes, high severity

Decay parameters:
- `ruin_integrity ∈ [0..1]`
- `path_condition ∈ [0..1]` (movement bonus scales with condition)
- `clear_level ∈ {light,medium,heavy}` with regrowth hint

## Outputs (Artifacts)
Directory: `MapGenerator/AncientCivilization/outbox/`

- `settlements.json` — settlement centers & footprints
- `ruins.json` — foundations and wall segments
- `ancient_paths.json` — polylines with condition & movement bonus
- `reclaimed_resources.json` — caches & cleared patches
- `collapse_reason.txt` — single-line code & brief note

### JSON Schemas (examples)

`settlements.json`
```json
{
  "version": 1,
  "job_id": "<uuid>",
  "settlements": [
    {
      "id": "S1",
      "center": {"x": 218, "y": 214},
      "score": 0.76,
      "footprint": {"radius": 16, "orientation": "slope_vec", "bounds": [ {"x":200, "y":198}, {"x":236, "y":230} ]},
      "abandonment": {"stage": "mid", "causes": ["flooding", "overextension"], "severity": 0.62}
    }
  ]
}
```

`ruins.json`
```json
{
  "version": 1,
  "job_id": "<uuid>",
  "ruins": [
    {
      "settlement_id": "S1",
      "type": "foundation",
      "polygon": [ {"x":212,"y":206}, {"x":224,"y":206}, {"x":224,"y":218}, {"x":212,"y":218} ],
      "integrity": 0.55
    },
    {
      "settlement_id": "S1",
      "type": "wall_segment",
      "line": [ {"x":212,"y":206}, {"x":224,"y":206} ],
      "integrity": 0.43
    }
  ]
}
```

`ancient_paths.json`
```json
{
  "version": 1,
  "job_id": "<uuid>",
  "paths": [
    {
      "from": "settlement:S1",
      "to": "resource:lumber:L1",
      "polyline": [ "218,214", "217,214", "216,214", "215,214", "214,214", "213,214" ],
      "condition": 0.68,
      "movement_bonus": 0.10
    }
  ]
}
```

`reclaimed_resources.json`
```json
{
  "version": 1,
  "job_id": "<uuid>",
  "caches": [
    { "type": "stone", "x": 220, "y": 216, "units": 120 },
    { "type": "wood",  "x": 224, "y": 218, "units": 90 }
  ],
  "cleared_patches": [
    { "center": {"x": 218, "y": 214}, "radius": 12, "clear_level": "medium" }
  ]
}
```

`collapse_reason.txt`
```
climate_shift + overextension — elevated severity with long travel costs
```

## Downstream Influence
- Tree regrowth suppression: `cleared_patches` inform TreePlanter to reduce initial trees.
- Movement: `ancient_paths.movement_bonus` feeds PathFinder/Gameplay to slightly boost speed.
- Feature hints: WorldFeatures may align ramps or caverns near `ruins`/`settlements`.
- Player start suggestion: pick highest `settlement.score` as implicit start area.

## Determinism & Performance
- All randomness replaced by hashed tie-breakers.
- Single pass scoring + nearest-neighbor queries.
- Uses existing PathFinder routes for connectivity; no agent search.

## TYS Plan (summary)
1. Inputs exist? Verify files are present (heightmap, water, climate, resources, pathfinder).
2. Run stage: produce artifacts in outbox.
3. Validate:
   - Settlement count 1–3
   - Paths connect centers to at least 2 resource zones
   - Ruins polygons inside footprints
   - Movement bonuses ∈ [0,0.2]
   - collapse_reason.txt non-empty
4. Integrate:
   - Confirm TreePlanter/WorldFeatures consume hints
   - PathFinder recognizes movement bonuses
