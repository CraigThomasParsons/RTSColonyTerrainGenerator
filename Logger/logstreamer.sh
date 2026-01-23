#!/usr/bin/env bash
# MapGenerator LogStreamer — intentionally simple aggregator
# Watches stage log directories, normalizes lines (now JSONL-aware), and appends to logs/mapgen.log.
# Rules: append-only output, path-based stage detection, minimal state (no buffering beyond offsets), and single writer.

set -euo pipefail
shopt -s nullglob

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_LOG="${ROOT_DIR}/logs/mapgen.log"
PIPE_DIR="$(mktemp -d -t mapgen-logstreamer.XXXXXX)"
PIPE_PATH="${PIPE_DIR}/stream.pipe"

mkdir -p "${ROOT_DIR}/logs"
mkfifo "${PIPE_PATH}"

# Central writer to enforce single-writer semantics and avoid interleaved writes.
cat "${PIPE_PATH}" >> "${OUTPUT_LOG}" &
WRITER_PID=$!
# Keep one write FD for all emitters to avoid opening/closing the FIFO repeatedly.
exec 3>"${PIPE_PATH}"

declare -A WATCHED
PIDS=()

# Explicit globs keep this dumb: no config files, just known locations.
PATTERNS=(
  "${ROOT_DIR}/Heightmap/logs/"'*.log'
  "${ROOT_DIR}/Heightmap/logs/"'*.log.jsonl'
  "${ROOT_DIR}/Tiler/logs/"'*.log'
  "${ROOT_DIR}/Tiler/logs/"'*.log.jsonl'
  "${ROOT_DIR}/Weather/logs/"'*.log'
  "${ROOT_DIR}/Weather/logs/"'*.log.jsonl'
  "${ROOT_DIR}/TreePlanter/logs/"'*.log'
  "${ROOT_DIR}/TreePlanter/logs/"'*.log.jsonl'
  "${ROOT_DIR}/World/logs/"'*.log'
  "${ROOT_DIR}/World/logs/"'*.log.jsonl'
  "${ROOT_DIR}/logs/jobs/"'*/*.log'
  "${ROOT_DIR}/logs/jobs/"'*/*.log.jsonl'
)

cleanup() {
  for pid in "${PIDS[@]:-}"; do
    kill "$pid" 2>/dev/null || true
  done
  exec 3>&-
  kill "${WRITER_PID}" 2>/dev/null || true
  rm -f "${PIPE_PATH}"
  rmdir "${PIPE_DIR}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Extract job ID from /logs/jobs/<job-id>/... paths.
# Job IDs only live under logs/jobs/<job-id>/, otherwise unknown is safer than guessing.
job_from_path() {
  local path="$1"
  if [[ "${path}" =~ /logs/jobs/([^/]+)/ ]]; then
    echo "${BASH_REMATCH[1]}"
  else
    echo "unknown"
  fi
}

# Stage inference is path-only on purpose; no content parsing.
stage_from_path() {
  local path="$1"
  local lower_path="${path,,}"
  case "${lower_path}" in
    *"/heightmap/logs/"*) echo "heightmap" ;;
    *"/tiler/logs/"*) echo "tiler" ;;
    *"/weather/logs/"*) echo "weather" ;;
    *"/treeplanter/logs/"*) echo "treeplanter" ;;
    *"/world/logs/"*) echo "world" ;;
    *"/logs/jobs/"*)
      local base
      base="$(basename "${path}")"
      base="${base%.log}"
      echo "${base,,}"
      ;;
    *) echo "unknown" ;;
  esac
}

# Normalize every line through jq into TEXT format; invalid JSON becomes a wrapped raw line.
emit_json_line() {
  local stage="$1"
  local job="$2"
  local line="$3"
  local now_iso normalized
  now_iso="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

  normalized="$(
    jq -R -r \
      --arg stage "${stage}" \
      --arg job "${job}" \
      --arg now "${now_iso}" \
      '
        def norm_ts($t):
          if ($t|type=="number") then ($t/1000 | floor | todateiso8601)
          elif ($t|type=="string") then $t
          else $now end;

        def norm_level($v):
          if ($v|type=="string") then ($v|ascii_upcase) else "INFO" end;

        def normalize($rec):
          {
            ts: norm_ts($rec.ts),
            stage: ($rec.stage // $stage // "unknown"),
            job: ($rec.job // $rec.job_id // $job // "unknown"),
            level: norm_level($rec.level),
            msg: ($rec.msg // ""),
          };

        (try (fromjson | normalize(.)) catch {ts:$now, stage:$stage, job:$job, level:"INFO", msg:.})
        | "\(.ts) [job=\(.job)] [stage=\(.stage)] \(.level) \(.msg)"
      ' <<<"${line}"
  )"

  printf '%s\n' "${normalized}" >&3
}

# One watcher per file; tail -n0 prevents duplication on restart and -F tolerates rotations.
launch_watcher() {
  local file="$1"
  local stage="$2"
  local job="$3"
  tail -n0 -F --retry "${file}" |
    while IFS= read -r line || [[ -n "${line}" ]]; do
      emit_json_line "${stage}" "${job}" "${line}"
    done &
  PIDS+=($!)
}

# Polling is simple and dependency-free; inotifywait is avoided to keep setup minimal.
scan_for_logs() {
  local pattern
  for pattern in "${PATTERNS[@]}"; do
    local files=()
    mapfile -t files < <(compgen -G "${pattern}" || true)
    for file in "${files[@]}"; do
      [[ -f "${file}" ]] || continue
      # Never watch the aggregated output file even if patterns expand oddly.
      if [[ -z "${WATCHED[${file}]+x}" ]] && [[ "${file}" != "${OUTPUT_LOG}" ]]; then
        WATCHED["${file}"]=1
        launch_watcher "${file}" "$(stage_from_path "${file}")" "$(job_from_path "${file}")"
      fi
    done
  done
}

while true; do
  scan_for_logs
  sleep 2
done
