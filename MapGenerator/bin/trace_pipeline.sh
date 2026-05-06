#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$HOME/Code/RTSColonyTerrainGenerator}"
WIDTH="${WIDTH:-64}"
HEIGHT="${HEIGHT:-64}"
DURATION="${DURATION:-120}"
UNTIL="${UNTIL:-treeplanter}"
FOLLOW_ONLY="${FOLLOW_ONLY:-0}"
LOG_PATH="${LOG_PATH:-$REPO_ROOT/logs/mapgen.log}"

mkdir -p "$(dirname "$LOG_PATH")"
touch "$LOG_PATH"

ARGS=(
  "--width" "$WIDTH"
  "--height" "$HEIGHT"
  "--duration" "$DURATION"
  "--log" "$LOG_PATH"
  "--stargus-export"
  "--run-stargus-consumer"
  "--stargus-timeout" "120"
  "--stargus-consumer-timeout" "120"
)

if [[ "$FOLLOW_ONLY" == "1" ]]; then
  ARGS+=("--follow-only")
else
  ARGS+=("--until" "$UNTIL")
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"

echo "[trace] Running pipeline_ai_test with args:"
printf '  %q' "$PYTHON_BIN" "$REPO_ROOT/tools/pipeline_ai_test/pipeline_ai_test.py" "${ARGS[@]}"
echo

"$PYTHON_BIN" "$REPO_ROOT/tools/pipeline_ai_test/pipeline_ai_test.py" "${ARGS[@]}"

echo
echo "[trace] Artifact report:"
"$REPO_ROOT/MapGenerator/bin/trace_pipeline_report.sh"
