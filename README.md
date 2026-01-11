# RTS Colony Terrain Generator

A modular, deterministic terrain generation pipeline for an RTS colony simulation game. The system implements a sophisticated multi-stage approach to procedurally generate complete game worlds including heightmaps, terrain tiling, weather patterns, and vegetation placement.

## Table of Contents
- [Overview](#overview)
- [Project Architecture](#project-architecture)
- [Pipeline Stages](#pipeline-stages)
- [Components](#components)
- [Getting Started](#getting-started)
- [Development Guide](#development-guide)
- [Project History](#project-history)
- [License](#license)

## Overview

This project implements a **modular, file-based terrain generation pipeline** using multiple programming languages for optimal performance:
- **Rust** for high-performance computational engines (Heightmap, Weather Analysis)
- **C# (.NET)** for deterministic tile processing (Tiler)
- **PHP** for flexible vegetation and world assembly (TreePlanter)
- **Python** for orchestration and monitoring tools (mapgenctl)
- **Bash** for system integration and job processing

### Key Features
- ✅ **Deterministic Generation**: Same input parameters always produce identical output
- ✅ **Systemd-Orchestrated**: Automated pipeline execution using Linux systemd path units
- ✅ **File-Based IPC**: Stages communicate via filesystem artifacts (no network, no databases)
- ✅ **Immutable Artifacts**: Binary data formats for performance and reliability
- ✅ **Observable Pipeline**: Live TUI monitoring with job logs and stage progress
- ✅ **Modular Design**: Each stage is independently deployable and testable

## Project Architecture

### Architectural Patterns

#### Micro-Kernel Architecture
Each pipeline stage (Heightmap, Weather, Tiler, TreePlanter, WorldFeatures) is an isolated, independent unit that:
- Reads from its own `inbox/` directory
- Processes data deterministically
- Writes output to `outbox/` directory
- Archives successful jobs or moves failures to `failed/`

#### File-Based Inter-Process Communication
Components communicate **strictly** via filesystem directories:
- `inbox/`: Incoming job JSON files trigger processing
- `outbox/`: Completed binary artifacts (`.heightmap`, `.maptiles`, `.weather`)
- `archive/`: Successfully processed jobs for audit trail
- `failed/`: Jobs that encountered errors for debugging
- `debug/`: Optional human-readable debug exports (BMP, HTML, PNG)

#### Systemd Orchestration
Each stage has a `.path` unit that watches its inbox directory and triggers a corresponding `.service` unit when new files appear:
```
Job File → inbox/ → systemd.path detects → systemd.service executes → outputs to outbox/
```

#### DAG-Based Pipeline Flow
The pipeline implements a directed acyclic graph (DAG) with parallel fan-out:
```
HeightmapApi (HTTP) → Heightmap Engine
                           ↓
                      .heightmap file
                      ↙           ↘
                 Tiler          Weather
              (parallel)        (parallel)
                  ↓                 ↓
              .maptiles         .weather
                      ↘           ↙
                      TreePlanter (fan-in)
                           ↓
                    WorldPayload (final output)
```

### Data Contracts

#### Binary Formats
Heavy data is transmitted in custom binary formats to avoid JSON parsing overhead:

**Heightmap Format** (`.heightmap`):
```
[HEADER: width, height, metadata]
[HEIGHT_DATA: u8 array of elevation values 0-255]
[LAYER_DATA: u8 array of terrain type IDs]
```

**Weather Format** (`.weather`):
```
[Per-cell weather analysis data]
```

**MapTiles Format** (`.maptiles`):
```
[Tile grid with resolved tile IDs based on adjacency masks]
```

### Code Style Standards
- **Clarity over Brevity**: Descriptive variable names (e.g., `displacement_amount_per_iteration` not `disp`)
- **Explicit Types**: Type annotations even when inference is possible
- **No Magic**: Logic is commented and explained
- **Fail-Fast**: Errors move jobs to `failed/` with descriptive messages
- **Determinism First**: All randomness is seeded; no system time or external entropy

## Pipeline Stages

### 1. HeightmapApi (PHP)
**Purpose**: HTTP API frontend for job submission  
**Location**: `HeightmapApi/`  
**Technology**: PHP with Composer, Docker-ready  
**Responsibility**: Accept job requests via REST API and write job JSON files to Heightmap inbox

### 2. Heightmap Engine (Rust)
**Purpose**: Generate base terrain heightmap and terrain layers  
**Location**: `MapGenerator/Heightmap/`  
**Technology**: Rust with Cargo  
**Input**: Job JSON with seed, dimensions, generation parameters  
**Output**: Binary `.heightmap` file with elevation and terrain layer data  
**Features**:
- Perlin/Simplex noise-based terrain generation
- Deterministic seeding from job metadata
- Multi-octave fractal generation
- Binary format for performance

### 3. Tiler (C#/.NET)
**Purpose**: Convert heightmap cells into renderable tile IDs  
**Location**: `MapGenerator/Tiler/`  
**Technology**: C# (.NET)  
**Input**: `.heightmap` file from Heightmap Engine  
**Output**: `.maptiles` file with resolved tile IDs  
**Features**:
- 4-bit N/E/S/W adjacency bitmask calculation (0-15)
- Tile ID resolution: `(terrain_layer << 8) | adjacency_mask`
- Each cell expands to 2×2 tile block
- Optional HTML debug export for visual inspection

### 4. Weather Analysis (Rust)
**Purpose**: Generate weather patterns based on terrain  
**Location**: `MapGenerator/WeatherAnalyses/`  
**Technology**: Rust with Cargo  
**Input**: `.heightmap` file from Heightmap Engine  
**Output**: `.weather` file with per-cell weather data  
**Features**:
- Elevation-based temperature and precipitation
- Wind pattern simulation
- Climate zone determination

### 5. TreePlanter (PHP)
**Purpose**: Place vegetation based on terrain and weather suitability  
**Location**: `MapGenerator/TreePlanter/`  
**Technology**: PHP with Composer, PSR-4 autoloading  
**Input**: `.maptiles` and `.weather` files (fan-in)  
**Output**: World payload directory with tree placements  
**Features**:
- Deterministic tree placement algorithm
- Suitability calculation based on terrain + weather + density
- Multiple tree type support
- Debug exports (ASCII, PNG visualization)

### 6. WorldFeatures
**Purpose**: Final world assembly and feature placement  
**Location**: `MapGenerator/WorldFeatures/`  
**Status**: Planned integration point for minerals, starting locations, etc.

## Components

### mapgenctl - Pipeline Control Tool
**Location**: `tools/mapgenctl/`  
**Language**: Python  
**Features**:
- Live TUI dashboard for pipeline monitoring
- Stage completion detection via filesystem artifacts
- Parallel execution tracking (fan-out stages)
- Job log aggregation and viewing
- Systemd service diagnostics

**Usage**:
```bash
# Start pipeline with live monitoring
./tools/mapgenctl/cli.py run --job-id test_001 --watch

# View pipeline status
./tools/mapgenctl/cli.py status

# Tail logs for a specific job
./tools/mapgenctl/cli.py logs --job-id test_001
```

### Formal Specifications (Dafny)
**Location**: `specs/`  
**Purpose**: Design-time contracts for logging and data structures  
**Technology**: Dafny formal verification language  
**Note**: Specs are for documentation and verification only; generated code is not used in runtime

### Systemd Services
Each stage includes:
- `.path` unit: Watches inbox directory for new files
- `.service` unit: Executes processing script/binary
- `install.sh`: Script to install systemd units to `~/.config/systemd/user/`

## Getting Started

### Prerequisites
- **Rust**: 1.70+ with Cargo
- **.NET SDK**: 7.0+ for Tiler
- **PHP**: 8.4+ with Composer for TreePlanter and HeightmapApi
- **Python**: 3.8+ for mapgenctl tools
- **Systemd**: User services enabled (`loginctl enable-linger $USER`)

### Installation

#### 1. Clone Repository
```bash
git clone https://github.com/CraigThomasParsons/RTSColonyTerrainGenerator.git
cd RTSColonyTerrainGenerator
```

#### 2. Build Heightmap Engine
```bash
cd MapGenerator/Heightmap
./bin/build.sh  # Builds Rust heightmap engine
./install.sh    # Installs systemd units
cd ../..
```

#### 3. Build Tiler
```bash
cd MapGenerator/Tiler
./build.sh      # Builds .NET tiler
./systemd/install.sh
cd ../..
```

#### 4. Install TreePlanter
```bash
cd MapGenerator/TreePlanter
./install.sh    # Installs Composer dependencies and systemd units
cd ../..
```

#### 5. Configure Environment
```bash
cp .env.example MapGenerator/.env
# Edit .env to enable debug outputs if desired
```

#### 6. Start Systemd Services
```bash
systemctl --user daemon-reload
systemctl --user enable --now heightmap-queue.path
systemctl --user enable --now tiler.path
systemctl --user enable --now treeplanter.path
```

### Running a Test Job

#### Via HeightmapApi:
```bash
cd HeightmapApi
docker-compose up -d
curl -X POST http://localhost:8080/api/generate -d '{"width": 64, "height": 64, "seed": 12345}'
```

#### Direct Job Submission:
```bash
# Create test job file
cat > test_job.json << EOF
{
  "job_id": "test_001",
  "width": 64,
  "height": 64,
  "seed": 12345,
  "octaves": 4,
  "persistence": 0.5
}
EOF

# Submit to Heightmap inbox
cp test_job.json MapGenerator/Heightmap/inbox/

# Watch pipeline progress
./tools/mapgenctl/cli.py run --job-id test_001 --watch
```

## Development Guide

### Adding a New Pipeline Stage

#### 1. Use Scaffolding Tool
```bash
./tools/create_module.sh MyNewStage
```

This creates the standard directory structure:
```
MapGenerator/MyNewStage/
├── inbox/
├── outbox/
├── archive/
├── failed/
├── debug/
├── bin/
├── systemd/
│   ├── mynewstage.path
│   └── mynewstage.service
├── install.sh
└── README.md
```

#### 2. Implement Processing Logic
- Parse input JSON job file from `inbox/`
- Read any required binary artifacts (e.g., `.heightmap`)
- Process data **deterministically** (use seeded RNG)
- Write binary output to `outbox/`
- Move job file to `archive/` on success or `failed/` on error

#### 3. Follow Stage Contract
See `docs/Stage_Contract.md` for detailed requirements:
- One-file-in, one-file-out semantics
- Atomic file operations (write to temp, then rename)
- Proper error handling and logging
- Exit codes: 0 for success, non-zero for failure

#### 4. Add Logging
Use the standardized logging format:
```
[STAGE_NAME] [LEVEL] job_id=<id> | <message>
```

See examples in:
- `MapGenerator/Heightmap/heightmap-engine/src/stage_logger.rs` (Rust)
- `MapGenerator/Tiler/Logging/MapGenStageLogger.cs` (C#)
- `MapGenerator/TreePlanter/src/Logging/StageLogger.php` (PHP)

#### 5. Install and Test
```bash
cd MapGenerator/MyNewStage
./install.sh
systemctl --user restart mynewstage.service
echo '{"job_id":"test","width":32,"height":32}' > inbox/test.json
```

### Debug Outputs
Debug outputs are **strictly separated** from pipeline artifacts:
- Pipeline: `inbox/`, `outbox/`, `archive/` contain only machine-readable formats
- Debug: `debug/` contains human-readable exports (BMP, HTML, PNG, ASCII)
- Enable via `.env` configuration:
  ```
  HEIGHTMAP_DEBUG_BMP=1
  TILER_DEBUG_HTML=1
  TREEPLANTER_DEBUG_PNG=1
  ```

### Testing
Each component includes test infrastructure:
- Rust: `cargo test`
- .NET: Test projects in `Tiler/`
- PHP: PHPUnit tests in `TreePlanter/tests/`

## Project History

This project has evolved significantly since its inception in December 2025. Key milestones:

### Phase 1: Foundation (Dec 24, 2025)
- **Initial Setup**: Repository created with basic folder structure
- **HeightmapApi**: PHP REST API for job submission with Docker support
- **Heightmap Engine**: Rust-based terrain generation with binary output format

### Phase 2: Core Pipeline (Dec 25-26, 2025)
- **Deterministic Generation**: Implemented seeded RNG for reproducible maps
- **Systemd Integration**: Path-based triggering for automated processing
- **Watch Mode**: Added live pipeline monitoring with `mapgenctl --watch`
- **Debug Infrastructure**: BMP exports for heightmap visualization
- **Environment Configuration**: Centralized `.env` for debug flags

### Phase 3: Tiler Stage (Dec 27, 2025)
- **Adjacency Masking**: 4-bit bitmask calculation for tile selection
- **Binary Format Reader**: Strict `.heightmap` parsing and validation
- **HTML Debug Export**: Visual tile grid inspection capability
- **Systemd Worker**: One-file-in/one-file-out processing wrapper
- **Archive Handling**: Proper cleanup and artifact management

### Phase 4: TreePlanter Stage (Dec 28, 2025)
- **PHP Implementation**: Composer-based PSR-4 project structure
- **Vegetation Algorithm**: Suitability-based tree placement
- **Tile Assembly**: Parse `.maptiles` format and reconstruct grid
- **World Payload**: Directory-based output with tree placement data
- **Systemd Units**: Path + service integration

### Phase 5: Pipeline Orchestration (Dec 28, 2025 - Jan 2, 2026)
- **DAG-Aware Runner**: Python-based pipeline with stage dependencies
- **Parallel Fan-Out**: Tiler and Weather run concurrently after Heightmap
- **Fan-In Gating**: TreePlanter waits for both Tiler and Weather completion
- **Live TUI**: Curses-based real-time pipeline progress dashboard
- **Artifact-Based Completion**: Filesystem state as single source of truth

### Phase 6: Logging and Observability (Jan 3-7, 2026)
- **Structured Logging**: Unified format across Rust, C#, and PHP stages
- **Stage Loggers**: Consistent INFO/ERROR logging with job context
- **Job Log Aggregation**: Centralized logs under `logs/jobs/<job_id>/`
- **TUI Integration**: Live log streaming in pipeline dashboard
- **Error Visibility**: TreePlanter and all stages now fail loudly

### Phase 7: Pipeline Stabilization (Jan 7, 2026)
- **Symlink to Directory**: Fixed fan-out by replacing symlinks with real directories
- **Explicit Copying**: Heightmap copied to both Tiler and Weather inboxes
- **Service Restart Safety**: Forced symlink installation to prevent stale units
- **Executable Permissions**: Fixed wrapper script execution issues
- **End-to-End Verification**: Complete pipeline runs from Heightmap to WorldPayload

### Phase 8: Weather Analysis Stage
- **Rust Implementation**: Weather simulation based on terrain
- **Climate Zones**: Temperature and precipitation by elevation
- **Binary Format**: Efficient `.weather` output format
- **Systemd Integration**: Parallel execution alongside Tiler

### Technical Achievements
- ✅ **Zero Network Dependencies**: Pure filesystem-based pipeline
- ✅ **Multi-Language Integration**: Rust + C# + PHP + Python working together
- ✅ **Production-Ready Logging**: Structured, parseable, observable
- ✅ **Restart-Safe Design**: All stages handle interruption gracefully
- ✅ **Deterministic Throughout**: Every stage produces reproducible results
- ✅ **Observable Pipeline**: Real-time visibility into all stages

### Documentation Evolution
- **Formal Specifications**: Dafny specs for logging contracts
- **Stage Contracts**: Explicit requirements for new stage development
- **Environment Docs**: Configuration and debug flag documentation
- **Context Documents**: Detailed rationale and design decisions per stage

## Contributing

### Code Style
Follow the established patterns for each language:
- **Rust**: See `docs/MapGenerator/Heightmap/docs/rust_style.md`
- **PHP**: See `docs/php_style.md`
- **C#**: Follow .NET conventions with explicit types

### Pull Requests
1. Ensure all stages build successfully
2. Test with deterministic job (same seed should produce identical output)
3. Verify systemd units install and trigger correctly
4. Update relevant documentation
5. Add entry to appropriate `docs/history.md` or `CHANGELOG.md`

### Issues
Report bugs or request features via GitHub Issues. Include:
- Stage(s) affected
- Job parameters that trigger the issue
- Expected vs actual behavior
- Relevant log excerpts

## License

See [LICENSE](LICENSE) file for details.

---

**Note**: This project is under active development. The pipeline architecture is stable, but individual stages may receive enhancements and optimizations. See `todo.md` for planned improvements.