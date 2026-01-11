# MapGenerator Stage Contract

This document defines the **standard structure, responsibilities, and integration rules**
for any stage in the MapGenerator pipeline.

It is written to be understood by:
- Humans
- Automation scripts
- AI agents adding new stages

The goal is **consistency without rigidity**.

---

## Core Philosophy

- Each stage is **isolated**
- Each stage is **deterministic**
- Each stage communicates **only via files**
- Stages may be written in **any language**
- Bash is used as the universal wrapper
- systemd is used for automation
- The world must remain **playable**

Stages may:
- Analyze
- Transform
- Create
- Destroy
- Repair
- Invent infrastructure

There are **no thematic restrictions** at this level.

---

## Required Directory Structure

Every stage **must** follow this layout:

```
StageName/
├── inbox/
├── outbox/
├── archive/
├── failed/
├── debug/
├── bin/
├── docs/
├── systemd/
├── install.sh
└── README.md
```

Optional directories are allowed, but these are the baseline contract.

---

## Directory Responsibilities

### `inbox/`

**Purpose:**  
Incoming work items.

**Rules:**
- Files appear here when upstream stages finish
- Each file represents **one job**
- Files are immutable once detected
- The stage must not write to inbox

**Examples:**
- `.heightmap`
- `.tiles`
- `.features`
- `.json`
- `.bin`

---

### `outbox/`

**Purpose:**  
Authoritative outputs of this stage.

**Rules:**
- Exactly what downstream stages consume
- One logical output per input job (unless explicitly documented otherwise)
- No debug data
- No temporary files

Downstream stages must be able to trust outbox blindly.

---

### `archive/`

**Purpose:**  
Completed jobs.

**Rules:**
- Input files are moved here after successful processing
- Files are never modified
- Used for:
  - Auditing
  - Reprocessing
  - Debug replay

---

### `failed/`

**Purpose:**  
Failed jobs.

**Rules:**
- Input files are moved here on failure
- Failure reason should be logged
- Files are preserved for inspection
- No automatic retry unless explicitly implemented

---

### `debug/`

**Purpose:**  
Human-visible diagnostics.

**Rules:**
- NOT consumed by automation
- May include:
  - PNGs
  - SVGs
  - Logs
  - Annotated maps
- Safe to delete at any time
- No correctness guarantees

Debug exists to help *you*, not the pipeline.

---

### `bin/`

**Purpose:**  
Executable artifacts.

**Rules:**
- Compiled binaries live here
- Scripts that do real work live here
- Must be callable from bash
- Must fail loudly and clearly

Examples:
- Rust binaries
- Go binaries
- Python entrypoints
- PHP scripts
- C# executables

---

### `docs/`

**Purpose:**  
Human + AI understanding.

**Minimum Recommended Files:**
- `context.md` – why this stage exists
- `README.md` – how it works
- Any additional design docs

Docs are considered **part of the API**.

---

### `systemd/`

**Purpose:**  
Automation wiring.

**Contents:**
- `.service` units
- `.path` units
- Optional timers

**Rules:**
- Uses **user-level systemd**
- Watches inbox
- Triggers processing
- Never blocks the system

---

## Processing Model

### One Job = One Input File

The canonical flow:

1. systemd `.path` detects a new file in `inbox/`
2. systemd `.service` runs a wrapper script
3. Wrapper script:
   - Validates input
   - Invokes logic
   - Writes to `outbox/`
   - Moves input to `archive/` or `failed/`

No shared state.
No IPC.
No sockets.
No databases.

Files are the contract.

---

## Bash Wrapper Requirement

Regardless of implementation language, each stage **must** have
a bash-accessible entrypoint.

Typical pattern:

bin/consume_queue_job.sh


Responsibilities:
- Argument parsing
- Logging
- Error handling
- File movement
- Exit codes

---

## systemd Integration Pattern

Each stage typically uses:
- One `.path` unit
- One `.service` unit

Example `.path`:

```ini
[Path]
PathModified=%h/Code/RTSColonyTerrainGenerator/MapGenerator/StageName/inbox

Example .service:
```
[Service]
Type=oneshot
ExecStart=%h/Code/RTSColonyTerrainGenerator/MapGenerator/StageName/bin/consume_queue_job.sh
```
---

### Installation Contract

Every stage must provide an install.sh.

This script:

 - Creates required directories

 - Symlinks systemd units

 - Reloads systemd

 - Enables watchers

Example install.sh
```
#!/usr/bin/env bash
set -e

STAGE_DIR=~/Code/RTSColonyTerrainGenerator/MapGenerator/StageName
SYSTEMD_DIR=~/.config/systemd/user

mkdir -p "$SYSTEMD_DIR"

ln -sf "$STAGE_DIR/systemd/stage.service" "$SYSTEMD_DIR/"
ln -sf "$STAGE_DIR/systemd/stage.path" "$SYSTEMD_DIR/"

systemctl --user daemon-reload
systemctl --user enable --now stage.path
```
---

### Language Flexibility

Allowed:

- Bash

- Rust

- Go

- Python

- PHP

- C#

- C / C++

Any language that can be invoked from bash

Disallowed:

- Language-only solutions without a bash entrypoint

Bash is the glue.
Language is the implementation detail.

---

Determinism Expectations

Unless explicitly documented otherwise:

- Same input → same output

- No random sources without seed control

- No clock dependence

- No network access

---

