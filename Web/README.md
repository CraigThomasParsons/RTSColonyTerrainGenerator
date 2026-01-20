# PipelineDashboardKit

A read-only, file-backed, systemd-aware dashboard framework for observing pipeline stages.

## Installation & Running

### Option 1: Systemd Service (Recommended)

The dashboard can be installed as a user systemd service that runs automatically on startup and restarts on file changes.

```bash
./install.sh
```

This will:
1. Create the systemd service units in `~/.config/systemd/user/`
2. Enable the `web-dashboard.service` (runs on port 5001)
3. Enable the `web-dashboard.path` watcher (auto-restarts on code/config changes)

Once installed, view the dashboard at `http://localhost:5001`

To check status:
```bash
systemctl --user status web-dashboard.service
systemctl --user status web-dashboard.path
```

### Option 2: Manual Execution

#### Running MapGenerator Dashboard (Port 5001)

```bash
./run.sh --config pipelines/mapgenerator.yaml --port 5001
```

#### Running BandcampSync Dashboard (Port 5000)

```bash
./run.sh --config pipelines/bandcamp.yaml --port 5000
```

## dual-pipeline Setup

This dashboard supports multiple pipelines running on different ports or switched dynamically.

## Dashboard Features

### Multi-Stage Pipelines (MapGenerator)

The dashboard visualizes the flow of data through stages:
`Heightmap` → `Tiler` → `WeatherAnalyses` → `TreePlanter`

Each stage displays:

- **Inbox**: Files waiting to be processed.
- **Outbox**: Files successfully processed and moved.
- **Failed**: Files that caused errors (check logs).

### Single-Stage Pipelines (BandcampSync)

Visualizes internal queue states: `Pending`, `In Progress`, `Done`, `Failed`.

### Systemd Integration

Shows the status of background services using `systemctl --user`.

- **Green**: Active/Running
- **Gray**: Inactive/Waiting
- **Red**: Failed

## Observability Philosophy

This tool is strictly **Read-Only**.

- It **does not** trigger jobs.
- It **does not** retry failures (unless via external tools).
- It **does not** modify files.

### Why it cannot break the pipeline

1. **No Database**: It reads directly from the filesystem. There is no state to get out of sync.
2. **No Workers**: It performs no processing. It only counts files and reads logs.
3. **Isolated Port**: Running on 5001 ensures no conflict with existing tools.

### Interpreting State

- **Stalled**: If `Inbox` counts are high and `Outbox` is not increasing, or if the Systemd unit is not `Active`, the stage is likely stalled.
- **Failed**: Non-zero count in `Failed`. Check the Logs panel for details.
