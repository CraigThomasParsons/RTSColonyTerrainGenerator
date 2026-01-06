# Developer Tools Usage Guide

This document provides instructions for using the developer tools included in the **RTSColonyTerrainGenerator** project.

## Table of Contents

- [mapgenctl](#mapgenctl)
- [create_module.sh](#create_modulesh)

---

## mapgenctl

`mapgenctl` is the primary CLI tool for controlling the generation pipeline, submitting jobs, and inspecting the state of the system during development.

**Location**: `tools/mapgenctl/mapgenctl.py`

### Prerequisities

- Python 3.x
- curses support (standard on Linux/macOS) for TUI mode

### Basic Usage

You can run the tool directly from the project root:

```bash
./tools/mapgenctl/mapgenctl.py <command> [arguments]
```

### Commands

#### 1. `run` - End-to-End Pipeline Test

Runs a full pipeline test job. This submits a job and monitors it through all stages.

**Arguments:**

- `--width`: Map width in cells (required)
- `--height`: Map height in cells (required)
- `--until`: Stop monitoring after this stage (default: `treeplanter`)
  - Choices: `heightmap`, `tiler`, `weather`, `treeplanter`
- `--tui`: Enable the Terminal User Interface (live progress dashboard)

**Example:**

```bash
# Run a job and show simple text output
./tools/mapgenctl/mapgenctl.py run --width 512 --height 512

# Run with a cool TUI dashboard
./tools/mapgenctl/mapgenctl.py run --width 1024 --height 1024 --tui
```

#### 2. `submit-heightmap` - Manual Job Submission

Submits a job to the `heightmap` inbox without automatically monitoring it. Useful if you want to test the systemd triggers manually.

**Arguments:**

- `--width`: Map width in cells
- `--height`: Map height in cells
- `--watch`: (Optional) Watch the directory after submission

**Example:**

```bash
./tools/mapgenctl/mapgenctl.py submit-heightmap --width 256 --height 256
```

#### 3. `watch` - Monitor Stage Directories

Watches the `inbox`, `outbox`, and `archive` directories for a specific stage in real-time. Displays file additions and removals.

**Arguments:**

- `--stage`: The stage to watch (`heightmap`, `tiler`, `treeplanter`)

**Example:**

```bash
./tools/mapgenctl/mapgenctl.py watch --stage heightmap
```

#### 4. `clean` - Reset Stage State

**WARNING**: This deletes all files in the `inbox`, `outbox`, and `archive` for the specified stage. Use this to reset the environment for testing.

**Arguments:**

- `--stage`: The stage to clean

**Example:**

```bash
./tools/mapgenctl/mapgenctl.py clean --stage tiler
```

#### 5. `inspect-heightmap` & `build`

*Note: These commands are currently placeholders or under active development.*

---

## create_module.sh

This script creates the scaffolding for a new map generation module, following the project's strict architectural patterns.

**Location**: `tools/create_module.sh`

### Usage

```bash
./tools/create_module.sh <ModuleName>
```

**Arguments:**

- `<ModuleName>`: The PascalCase name of the new module (e.g., `RiverGenerator`).

### What it does

1. **Creates Directory Structure**: Generates `inbox`, `outbox`, `failed`, `systemd`, and `bin` directories in `MapGenerator/<ModuleName>`.
2. **Initializes Rust Project**: Creates a new Cargo binary project in `bin/<modulename>-engine`.
3. **Configures Dependencies**: Adds standard dependencies (`serde`, `serde_json`, `rand`) to `Cargo.toml`.
4. **Generates Boilerplate**: Writes a `main.rs` template that handles argument parsing for `job-file` and `output-file`.
5. **Creates Install Script**: Generates an `install.sh` script for building and deploying the binary.

### Example Workflow

```bash
# 1. Create the new module
./tools/create_module.sh RiverGenerator

# 2. Navigate to the module
cd MapGenerator/RiverGenerator

# 3. Implement your logic in bin/rivergenerator-engine/src/main.rs

# 4. Build and install
./install.sh
```
