#!/usr/bin/env bash
# night_shift_maintenance.sh — run one named maintenance task unattended.
#
# What it does:
#   Runs a single maintenance task by name, from a closed allowlist. Maintenance
#   jobs carry no issue and no branch: they are housekeeping that must be safe to
#   run on a schedule.
#
# Why it was created:
#   TheNightCrew dispatches two kinds of job, issue and maintenance, and its
#   client validates that BOTH entry points exist and are executable before it
#   will claim ANY job for a repository. A registry that only ships
#   night_shift.sh still gets maintenance jobs claimed and then stranded — the
#   exact take-then-strand failure the validation exists to prevent. See issue 33.
#
# How to run:
#   scripts/tools/night_shift_maintenance.sh <project_dir> <task_name>
#
# Called by TheNightCrew as:
#   night_shift_maintenance.sh /home/craigpar/Code/RTSColonyTerrainGenerator gitea-github-sync

set -euo pipefail

PROJECT_DIR="${1:?Usage: night_shift_maintenance.sh <project_dir> <task_name>}"
TASK_NAME="${2:?Usage: night_shift_maintenance.sh <project_dir> <task_name>}"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[night_shift_maintenance] $(ts) $*"; }

if [ ! -d "${PROJECT_DIR}/.git" ] && [ ! -f "${PROJECT_DIR}/.git" ]; then
    log "ABORT — not a git checkout: ${PROJECT_DIR}"
    exit 2
fi

LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOG_DIR}"
TASK_LOCK="${LOG_DIR}/night_shift_maintenance.lock"

if [ -f "${TASK_LOCK}" ]; then
    log "SKIP — lock file present: ${TASK_LOCK}"
    exit 0
fi
echo "$$" > "${TASK_LOCK}"
trap 'rm -f "${TASK_LOCK}"' EXIT

cd "${PROJECT_DIR}"

# A closed allowlist, not a dispatch-by-name-to-anything. An unattended runner
# that executes whatever string arrives from the board is a remote-execution
# hole; refusing an unknown name is the whole safety property here.
case "${TASK_NAME}" in
    gitea-github-sync)
        log "running gitea-github-sync"
        bash scripts/tools/sync_gitea_to_github.sh
        ;;
    quality)
        # Read-only verification. Reports rather than fixes, so a scheduled run
        # can never rewrite the tree behind a sleeping human.
        log "running quality gates (read-only)"
        just quality
        ;;
    *)
        log "ABORT — unknown maintenance task: ${TASK_NAME}"
        log "known tasks: gitea-github-sync, quality"
        exit 2
        ;;
esac

log "done — ${TASK_NAME}"
