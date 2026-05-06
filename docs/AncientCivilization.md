## Ancient Civilization (New Stage)

- Goal: Synthesize remnant proto-civilization artifacts deterministically.
- Inputs: Heightmap, Water, Climate, Resources, PathFinder routes.
- Outputs: settlements.json, ruins.json, ancient_paths.json, reclaimed_resources.json, collapse_reason.txt.

### TYS Checklist
- Build/Run stage to produce outbox artifacts
- Validate structure:
	- 1–3 settlements, each with footprint and abandonment
	- Ruin polygons within settlement footprints
	- Paths connect settlements to resource zones; movement_bonus ∈ [0,0.2]
	- collapse_reason.txt present and concise
- Downstream hooks:
	- TreePlanter uses cleared_patches to suppress early trees
	- PathFinder uses movement_bonus when present
	- WorldFeatures aligns features near ruins/settlements as hints

### Quick Commands
```bash
cd MapGenerator/AncientCivilization
./install.sh
# (future) ./ancientcivilization-engine --job-file inbox/<job>.json --output-file outbox
```

## WorldPreview (New Stage)

- Goal: Render a static, human-inspectable world preview (file:// capable).
- Inputs: PathFinder world payload (JSON) from PathFinder/outbox or WorldPreview/inbox.
- Outputs: outbox/<job_id> with index.html, style.css, main.js, world.json, assets/tileset.png, assets/colormap.png, assets/legend.png, README.md.

### TYS Checklist
- Build and run consumer once; verify outbox/<job_id>/ exists.
- Confirm assets exist: tileset.png shows ridges/trees/shorelines/ramps/roads; legend + colormap present.
- Open index.html via file:// and verify layers toggle (heightmap, tiles, features, paths), zoom/pan works, hover shows coords/height/tile/feature.
- Ensure world.json matches input payload and is pretty-printed.

### Quick Commands
```bash
cd MapGenerator/WorldPreview
./install.sh
bin/consume_worldpreview_job.sh
systemctl --user daemon-reload
systemctl --user enable --now worldpreview.path
```

## WorldSnapshot (New Stage)

- Goal: Render WorldPreview output into a single PNG snapshot of the full world.
- Inputs: WorldPreview outbox directory (index.html + assets).
- Outputs: outbox/<job_id>.png

### TYS Checklist
- Build/run consumer once; verify outbox/<job_id>.png exists.
- Confirm PNG contains full world (no missing edges) with UI hidden.
- Validate that the snapshot corresponds to the latest WorldPreview job.

### Quick Commands
```bash
cd MapGenerator/WorldSnapshot
./install.sh
bin/consume_worldsnapshot_job.sh
systemctl --user daemon-reload
systemctl --user enable --now worldsnapshot.path
```

## Playable (New Stage)

- Goal: Prepare world payloads for RTS gameplay (start zones + resources + labels).
- Inputs: WorldFeatures output (or InfrastructureBuilder output when available).
- Outputs: outbox/<job_id>.worldpayload + outbox/<job_id>.playable.json

### TYS Checklist
- Run consumer once; verify outbox/<job_id>.worldpayload exists.
- Verify outbox/<job_id>.playable.json exists and contains job_id.
- Confirm downstream exporters (StargusExport/CartridgeManufacturer) use Playable outbox by default.

### Quick Commands
```bash
cd MapGenerator/Playable
./install.sh
bin/consume_playable_job.sh
systemctl --user daemon-reload
systemctl --user enable --now playable.path
```

# TYS (Test Your S***t) Methodology

The **TYS Method** is the core development philosophy for this project. It emphasizes immediate, self-directed validation of every change before marking it as complete.

The goal is to prevent the accumulation of "hope-based code" by enforcing a tight feedback loop between implementation and verification.

## The Workflow

### 1. Implement

Make a change targeting a specific feature, behavior, or bug fix. Keep the scope focused enough to be verifiable.

### 2. Verify Immediately

**Do not wait for QA.** Test it yourself immediately using available tools.

* **Primary Tool**: `tools/pipeline_ai_test/pipeline_ai_test.py`
* **Alternative**: Unit tests, manual CLI runs (`mapgenctl`), or inspecting logs.

### 3. Loop or Proceed

* **If it fails**: Stop. Do not move on. Debug immediately. Go back to **Step 1** to fix the issue.
* **If it works**: Only then is the task considered "Done". You are now cleared to move to the next feature.

## Principles

* **Ownership**: You are responsible for proving your code works, not just writing it.
* **Immediacy**: The best time to fix a bug is seconds after you wrote it.
* **Evidence**: "It should work" is not acceptable. "I saw it work" is the standard.
