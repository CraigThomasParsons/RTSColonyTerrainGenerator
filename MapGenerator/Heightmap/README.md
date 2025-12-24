# Heightmap Modulewd

This module is responsible for generating heightmaps as part of the
MapGenerator pipeline.

It implements a **file-backed job queue** using:
- Bash (queue worker / orchestration)
- systemd **user units** (path + service)
- a future compiled engine (Rust) for heavy computation

The module is designed to be:
- self-contained
- installable via `install.sh`
- safe to use as a git submodule later
- compatible with other MapGenerator pipeline stages (e.g. Tiler)

---

## Directory Structure
```
Heightmap/
├── bin/
│ └── consume_heightmap_queue_job.sh # Queue worker (Bash)
├── inbox/ # Job queue (JSON files)
├── outbox/ # Output (symlink target for next stage)
├── archive/ # Successfully processed jobs
├── failed/ # Failed jobs
├── systemd/
│ └── heightmap-queue/
│ ├── heightmap-queue.path # systemd path unit
│ └── heightmap-queue.service # systemd service unit
├── install.sh # Installs systemd units
└── README.md
```

---

## Concept Overview

- Each `*.json` file placed into `inbox/` represents **one job**
- systemd watches the inbox using a `.path` unit
- When a new file appears, systemd triggers the worker service
- The worker:
  - claims one job atomically
  - generates output (placeholder for now)
  - archives the job
  - writes a single output file to `outbox/`

This replaces the need for a message broker during early development and
keeps everything transparent and debuggable.

---

## Requirements

- Linux with systemd
- systemd **user session** enabled
- Bash
- Rust
- No root access required

---

## Installation

After cloning or checking out this repository:

```bash
cd ~/MapGenerator/Heightmap
chmod +x install.sh
./install.sh
```

This will:

  - Symlink the systemd units into ~/.config/systemd/user/

  - Reload the systemd user daemon

  - Enable and start the inbox watcher

  Verify systemd is running
``` systemctl --user status heightmap-queue.path ```


Expected state:

Active: active (waiting)

Running a Simple Test Job
1. Create required directories (if not present)
mkdir -p inbox outbox archive failed

2. Drop a test job into the inbox
echo '{"test":"job_002"}' > inbox/test_job_002.json

3. Watch the worker run
journalctl --user -u heightmap-queue.service -f


You should see output similar to:

[heightmap-worker] Claimed job: test_job_002.json
[heightmap-worker] Generating placeholder output: ...
[heightmap-worker] Job completed successfully: test_job_002.json

4. Verify results
ls -la archive
ls -la outbox


Expected:

  - archive/ contains test_job_002.json

  - outbox/ contains test_job_002.heightmap


# Heightmap Engine (Fault-Line Generator)

This program is a standalone **Rust CLI tool** that generates a deterministic
terrain heightmap using a **fault-line algorithm**.

It is designed to be run by a worker process as part of a larger
filesystem-based queue pipeline.

---

## High-Level Overview

The heightmap engine performs the following steps:

1. Parse command-line arguments
2. Load a heightmap job definition from a JSON file
3. Generate terrain using a fault-line algorithm
4. Normalize height values into the range `0–255`
5. Write a single binary output file

The engine is **deterministic**:  
given the same job file, it will always produce the same output.

---

## Job Input Structure

The engine expects a JSON job file that matches the following Rust structure:

```rust
#[derive(Debug, Deserialize)]
struct HeightmapJob {
    job_id: String,
    map_width_in_cells: u32,
    map_height_in_cells: u32,
    fault_line_iteration_count: Option<u32>,
    random_seed: u64,
    requested_at_utc: String,
}
```
### Field meanings

- job_id:
A unique identifier used for logging and output naming.

- map_width_in_cells: / map_height_in_cells
The dimensions of the heightmap grid.

- fault_line_iteration_count (optional)

   How many fault iterations to run.
   
   If omitted, the engine uses a conservative default.

- random_seed
   Seed for the deterministic random number generator.
   
   This guarantees reproducible terrain.

- requested_at_utc:
Timestamp recorded by the API when the job was enqueued.

---

### Command-Line Interface

The engine is invoked as follows:
```
heightmap-engine --job-file <path> --output-file <path>
```

If the required arguments are missing, the program exits with an error and
prints usage instructions.

---

### Step-by-Step Execution
###  1. Parse command-line arguments
```
let arguments: Vec<String> = env::args().collect();
```
---
### The program expects exactly four arguments after the binary name:
```
--job-file <path>
```
```
--output-file <path>
```

Failing early prevents ambiguous behavior.

###   2. Load and parse the job file
```
let job_file_contents = fs::read_to_string(job_file_path)
    .expect("Failed to read job file");

let job: HeightmapJob = serde_json::from_str(&job_file_contents)
    .expect("Failed to parse job JSON");

```

- The job file is read as a UTF-8 string

- serde_json deserializes it into a strongly-typed Rust struct


-S Any failure causes an immediate, explicit exit

### 3. Allocate storage for height data
let total_cell_count =
    job.map_width_in_cells * job.map_height_in_cells;


Two data structures are prepared:
```
Height accumulator (signed)
let mut height_accumulator_values: Vec<i32> =
    vec![0; total_cell_count as usize];
```

### Uses signed integers

** Required because fault lines add and subtract values **

Normalized later into bytes

Output buffer (bytes)
```
let mut heightmap_bytes: Vec<u8> =
    Vec::with_capacity(total_cell_count as usize);

```

One byte per cell

Pre-allocated for performance and clarity

4. Configure deterministic randomness
```
let mut deterministic_rng: ChaCha8Rng =
    ChaCha8Rng::seed_from_u64(job.random_seed);
```

Uses ChaCha8Rng

Ensures identical output for identical input

No global or implicit randomness is allowed

5. Fault-line algorithm
Iteration count
```
let fault_line_iteration_count: u32 =
    job.fault_line_iteration_count.unwrap_or(50);
```

If the job does not specify an iteration count, a default is chosen that still
produces visible terrain features.

Core idea

Each iteration:

- Picks a random line across the map

- Determines which side of the line each cell lies on

- Adds or subtracts height accordingly

Repeating this process creates ridges and valleys.

Random line selection
```
let line_point_one_x: f32 = rng.gen_range(0.0..width);
let line_point_one_y: f32 = rng.gen_range(0.0..height);
```

Two random points define a line in floating-point space.
Floating point math simplifies geometric tests.

Degenerate line detection
```
if line_length_squared < 0.0001 {
    continue;
}
```

If the two points are almost identical, the line is skipped.
This avoids unstable geometry edge cases.

- Side-of-line test

For each cell:
```
cross = (cell - line_point_one) × line_direction


cross >= 0 → one side

cross < 0 → the other side
```

This signed cross product determines which displacement to apply.

Height displacement
```
if signed_cross_product_value >= 0.0 {
    height += displacement;
} else {
    height -= displacement;
}
```

Each iteration creates a “step” in the terrain.
Many iterations accumulate into mountain ridges.

### 6. Normalize heights to 0–255

After all fault iterations:

  1. Find the minimum and maximum accumulated height

  2. Compute the height range

  3. Scale each value into a byte
```
normalized = (value - min) / (max - min)
byte = normalized * 255
```
---

#### Flat map handling

If the height range is zero:
```
heightmap_bytes.push(128);
```
A neutral mid-gray value is written for every cell.

This avoids division-by-zero errors.
---
### 7. Write output file
```
fs::write(output_path, heightmap_bytes)
    .expect("Failed to write output heightmap file");
```

- Exactly one output file

- Binary format

- Row-major order

- One byte per cell

This file is designed to be consumed directly by the next pipeline stage
(the Tiler).
---

Output Format Summary

- Type: Binary

- Encoding: Unsigned 8-bit integers

- Layout: Row-major

- Value range: 0–255

---

### Design Guarantees

- Deterministic output

- No side effects outside declared paths

- One job → one file

- Explicit failure on error

- Readable, maintainable code

---

### Intentional Non-Goals (For Now)

- No erosion simulation

- No biome classification

- No image output

- No tiling logic

- No metadata output

These features are layered after the pipeline is stable.

---

Lock the layer model (simple & explicit)
We derive layers only from normalized height (0–255).

Layer definitions (v1, locked)
```
0   –  79   → Water
80  – 159   → Land
160 – 219   → PineMountain
220 – 255   → RockMountain
```

The idea here is if all heights are scaled, stretched or normalized to be between 0 - 255
Then tiles produced will be enough for each layer of the map.
---

