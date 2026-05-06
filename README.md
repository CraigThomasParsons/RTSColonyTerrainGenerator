# RTSColonyTerrainGenerator

The Map Generator for the RTS colony sim.

This project implements a modular, file-based terrain generation pipeline using Rust for high-performance computing and Systemd for orchestration.

## Project Analysis

### Architecture & Patterns
- **Micro-Kernel Architecture**: Each stage (Heightmap, Weather, Tiler, etc.) is an isolated, independent unit.
- **File-Based IPC**: Components communicate strictly via file system directories (`inbox`, `outbox`, `failed`, `archive`).
- **Systemd Orchestration**: `systemd.path` units monitor `inbox` directories to trigger processing services automatically.
- **Immutable Artifacts**: Heavy data is passed as binary artifacts (custom formats), avoiding JSON parsing for bulk data.
- **Determinism**: All generation is deterministic based on a seed. The same job parameters must always produce the exact same binary output.
- **Explicit Data Contracts**: Output formats are strictly defined (e.g., Header + Height Bytes + Layer Bytes) to ensure forward compatibility.

### Code Style Standards
- **Language**: Rust (Core Engines), Bash (Glue/Scripts).
- **Clarity over Brevity**: Variable names are descriptive and unabbreviated (e.g., `displacement_amount_per_iteration` instead of `disp`).
- **Explicit Types**: Type annotations are used even when type inference is possible, to prevent ambiguity (`let x: f32 = 1.0;`).
- **No "Magic"**: Logic is explained via comments. Algorithms focus on stability and reproducibility over complex "black box" simulations.
- **Error Handling**: Fail-fast philosophy for job processing (move to `failed` directory), with helpful error messages.

## Contributing Instructions

### 1. Scaffolding Tool
Run the helper script to create a new module:
```bash
./tools/create_module.sh <ModuleName>
```

### 2. Module Structure
New modules should follow the established directory structure:
```
Module/
├── bin/
│   └── module-engine/  (Rust project)
├── inbox/              (Incoming jobs)
├── outbox/             (Completed artifacts)
├── failed/             (Failed jobs)
├── systemd/            (Systemd unit files)
└── README.md           (Documentation)
```

### 3. Implementation Guidelines
- **Input**: Parse a JSON job file containing at least a `job_id`, `width`, `height`, and generation parameters.
- **Processing**: Use a determinstic RNG seeded from the job parameters.
- **Output**: Write binary files to the specified output path.
- **Logging**: Print progress to stdout/stderr (captured by journald).

### 4. Build & Deploy
- `cargo build --release`
- Copy binary to the execution location.
- Install/Reload systemd units.

## Roadmap
See `todo.md` for the current task list and optimization suggestions.

### Building the heightmap engine
```bash
cd MapGenerator/Heightmap/bin/heightmap-engine
cargo clean
cargo build --release
cp target/release/heightmap-engine ./heightmap-engine
chmod +x heightmap-engine
systemctl --user restart heightmap-queue.service
```