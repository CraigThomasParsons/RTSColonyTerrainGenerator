# Heightmap Module (MapGenerator)

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
