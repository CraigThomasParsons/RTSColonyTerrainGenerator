#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# LeftOff Snapshot Writer
# Produces an always-current recovery document and timestamped snapshots.
# File-first by design: no sockets, no DB, no external service dependency.
# -----------------------------------------------------------------------------

REPO_ROOT="${REPO_ROOT:-$HOME/Code/RTSColonyTerrainGenerator}"
MAPGEN_ROOT="${MAPGEN_ROOT:-$REPO_ROOT/MapGenerator}"
LEFTOFF_FILE="${LEFTOFF_FILE:-$REPO_ROOT/where_I_left_off.md}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-$REPO_ROOT/logs/leftoff_snapshots}"
NOTE="${1:-}"

mkdir -p "$(dirname "$LEFTOFF_FILE")"
mkdir -p "$SNAPSHOT_DIR"

NOW_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
STAMP="$(date -u +"%Y%m%d_%H%M%S")"
TMP_FILE="${LEFTOFF_FILE}.tmp"
SNAPSHOT_FILE="$SNAPSHOT_DIR/leftoff_${STAMP}.md"

find_latest_job_id() {
  local candidate
  local dir

  for dir in \
    "$MAPGEN_ROOT/Playable/outbox" \
    "$MAPGEN_ROOT/WorldFeatures/outbox" \
    "$MAPGEN_ROOT/TreePlanter/outbox" \
    "$MAPGEN_ROOT/StargusExport/outbox"
  do
    if [[ ! -d "$dir" ]]; then
      continue
    fi

    candidate="$(ls -t "$dir"/* 2>/dev/null | head -n1 || true)"
    if [[ -n "$candidate" ]]; then
      basename "$candidate" | sed -E 's/\.[^.]+$//'
      return
    fi
  done

  echo ""
}

print_stage_queue_summary() {
  local stage_dir
  local stage_name
  local inbox_count
  local outbox_count
  local failed_count

  for stage_dir in "$MAPGEN_ROOT"/*; do
    if [[ ! -d "$stage_dir" ]]; then
      continue
    fi
    stage_name="$(basename "$stage_dir")"

    # Only treat folder as stage if baseline queue dirs exist.
    if [[ ! -d "$stage_dir/inbox" ]] || [[ ! -d "$stage_dir/outbox" ]]; then
      continue
    fi

    inbox_count="$(find "$stage_dir/inbox" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l | tr -d ' ')"
    outbox_count="$(find "$stage_dir/outbox" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l | tr -d ' ')"
    failed_count="0"
    if [[ -d "$stage_dir/failed" ]]; then
      failed_count="$(find "$stage_dir/failed" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l | tr -d ' ')"
    fi

    echo "- ${stage_name}: inbox=${inbox_count}, outbox=${outbox_count}, failed=${failed_count}"
  done
}

GIT_BRANCH="(not a git repo)"
GIT_STATUS=""
if git -C "$REPO_ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  GIT_STATUS="$(git -C "$REPO_ROOT" --no-pager status --short 2>/dev/null | head -n 30 || true)"
fi

LATEST_JOB_ID="$(find_latest_job_id)"

{
  echo "# Where I Left Off"
  echo
  echo "## Snapshot"
  echo "- timestamp_utc: ${NOW_UTC}"
  echo "- branch: ${GIT_BRANCH}"
  if [[ -n "$LATEST_JOB_ID" ]]; then
    echo "- latest_job_id: ${LATEST_JOB_ID}"
  else
    echo "- latest_job_id: (none found)"
  fi
  if [[ -n "$NOTE" ]]; then
    echo "- operator_note: ${NOTE}"
  fi
  echo

  echo "## Stage Queue Summary"
  print_stage_queue_summary
  echo

  echo "## Git Status (top 30)"
  if [[ -n "$GIT_STATUS" ]]; then
    echo '```text'
    echo "$GIT_STATUS"
    echo '```'
  else
    echo "- clean or unavailable"
  fi
  echo

  echo "## Recovery Steps"
  echo "1. Review stage queue summary above."
  echo "2. Check failed lanes for blockers."
  echo "3. Run trace/report scripts or targeted stage consumers."
  echo "4. Update this snapshot note after major pipeline transitions."
  echo
} > "$TMP_FILE"

# Atomic replace to avoid partial writes during freezes/reboots.
mv "$TMP_FILE" "$LEFTOFF_FILE"
cp "$LEFTOFF_FILE" "$SNAPSHOT_FILE"

echo "[leftoff] Updated: $LEFTOFF_FILE"
echo "[leftoff] Snapshot: $SNAPSHOT_FILE"
