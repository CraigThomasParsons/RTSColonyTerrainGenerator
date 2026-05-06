#!/usr/bin/env bash
#
# CivicOverreach runner
#
# Responsibilities:
# - Accept a job_id
# - Locate Heightmap/outbox/<job_id>.heightmap
# - Copy artifacts into a working directory
# - Execute civic_overreach.py
# - Write output to SimulateCity/outbox/<job_id>.civic_overreach.worldpayload
# - Never mutate input artifacts
#

set -euo pipefail

JOB_ID="${1:-}"
if [[ -z "$JOB_ID" ]]; then
  echo "[CivicOverreach] Missing job_id" >&2
  exit 1
fi

REPO_ROOT="$HOME/Code/RTSColonyTerrainGenerator"
HEIGHTMAP_OUTBOX="$REPO_ROOT/MapGenerator/Heightmap/outbox"
STAGE_ROOT="$REPO_ROOT/MapGenerator/SimulateCity"

WORK_DIR="$STAGE_ROOT/inbox/$JOB_ID"
OUTBOX_DIR="$STAGE_ROOT/outbox"
LOG_DIR="$STAGE_ROOT/logs"

HEIGHTMAP_BIN="$HEIGHTMAP_OUTBOX/$JOB_ID.heightmap"
OUTPUT_FILE="$OUTBOX_DIR/$JOB_ID.civic_overreach.worldpayload"
LOG_FILE="$LOG_DIR/$JOB_ID.civic_overreach.log"

mkdir -p "$WORK_DIR" "$OUTBOX_DIR" "$LOG_DIR"

if [[ -f "$OUTPUT_FILE" ]]; then
  echo "[CivicOverreach] Output exists, skipping: $OUTPUT_FILE" | tee -a "$LOG_FILE"
  exit 0
fi

if [[ ! -f "$HEIGHTMAP_BIN" ]]; then
  echo "[CivicOverreach] Missing heightmap: $HEIGHTMAP_BIN" | tee -a "$LOG_FILE"
  exit 0
fi

PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

# Copy the heightmap binary into working dir for traceability
cp -f "$HEIGHTMAP_BIN" "$WORK_DIR/$JOB_ID.heightmap"

# Export PNG + meta into working dir (non-destructive)
"$PYTHON_BIN" \
  "$REPO_ROOT/MapGenerator/Heightmap/bin/export_heightmap_png.py" \
  --input "$HEIGHTMAP_BIN" \
  --output-dir "$WORK_DIR" \
  --job-id "$JOB_ID" \
  2>&1 | tee -a "$LOG_FILE"

# Run CivicOverreach
"$PYTHON_BIN" \
  "$STAGE_ROOT/bin/civic_overreach.py" \
  --input-dir "$WORK_DIR" \
  --output-dir "$OUTBOX_DIR" \
  --log-dir "$LOG_DIR" \
  2>&1 | tee -a "$LOG_FILE"

if [[ ! -f "$OUTPUT_FILE" ]]; then
  echo "[CivicOverreach] Output missing after run: $OUTPUT_FILE" | tee -a "$LOG_FILE"
  exit 0
fi

# Log summary counts
"$PYTHON_BIN" - <<'PY' 2>/dev/null | tee -a "$LOG_FILE"
import json
from pathlib import Path

output_path = Path("""$OUTPUT_FILE""")
if not output_path.exists():
    raise SystemExit(0)

payload = json.loads(output_path.read_text(encoding="utf-8"))
concrete = payload.get("concrete", {})
heuristics = payload.get("heuristics", {})

bridges = concrete.get("bridges", [])
roads = concrete.get("roads", [])
buildings = concrete.get("buildings", [])

overreach = heuristics.get("overreach_zones", [])

islands = [zone for zone in overreach if zone.get("type") == "island"]

disasters = heuristics.get("disaster_events", [])
maint = heuristics.get("maintenance_failures", [])

print("[CivicOverreach] islands_detected=", len(islands))
print("[CivicOverreach] bridges_attempted=", len(bridges))
print("[CivicOverreach] disasters_applied=", len(disasters) + len(maint))
print("[CivicOverreach] ruins_emitted=", len(bridges) + len(roads) + len(buildings))
PY
