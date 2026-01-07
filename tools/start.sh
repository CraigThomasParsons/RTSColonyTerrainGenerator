#!/usr/bin/env bash

set -euo pipefail

# mapgenctl
# ├── cli.py          ← orchestration / commands
# ├── __main__.py
# ├── utils/          ← shared, non-UI helpers
# │   ├── paths.py
# │   ├── joblog.py
# │   └── env.py (optional later)
# └── tui/            ← interactive UI subsystem
#     ├── model.py    ← UI data model (LogEntry, JobInfo)
#     ├── tailer.py   ← log tailing logic
#     ├── job_index.py
#     └── views.py

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MAPGENCTL_DIR="$SCRIPT_DIR/mapgenctl"


mkdir -p "$MAPGENCTL_DIR/tui"
mkdir -p "$MAPGENCTL_DIR/utils"

touch "$MAPGENCTL_DIR/cli.py"
touch "$MAPGENCTL_DIR/__main__.py"
touch "$MAPGENCTL_DIR/utils/paths.py"
touch "$MAPGENCTL_DIR/utils/joblog.py"
touch "$MAPGENCTL_DIR/tui/model.py"
touch "$MAPGENCTL_DIR/tui/tailer.py"
touch "$MAPGENCTL_DIR/tui/job_index.py"
touch "$MAPGENCTL_DIR/tui/views.py"

echo "Created mapgenctl skeleton structure in $MAPGENCTL_DIR"   