#!/usr/bin/env bash
# night_shift.sh — run one Gitea issue unattended, for TheNightCrew.
#
# What it does:
#   Claims a Gitea issue through this repository's own start_gitea_issue.py
#   (which writes the repo lock and creates the feature branch), launches an
#   agent against it, and returns the tree to main afterwards when it is safe to.
#
# Why it was created:
#   TheNightCrew's client refuses to claim any job for a repository until this
#   entry point exists and is executable — it fails closed rather than guessing
#   how to run the work. Without this file, no ticket in this repository can
#   ever be dispatched. See issue 33.
#
#   AMPB's equivalent delegates to start_gitea_issue.py --park-dirty --launch
#   and a prompt_generator.py chain. Neither exists here: this repository's
#   start_gitea_issue.py has no such flags, so copying AMPB's script would fail
#   at runtime. This one is deliberately self-contained.
#
# How to run:
#   scripts/tools/night_shift.sh <project_dir> <issue_number> [agent]
#
# Called by TheNightCrew as:
#   night_shift.sh /home/craigpar/Code/RTSColonyTerrainGenerator 42 claude

set -euo pipefail

PROJECT_DIR="${1:?Usage: night_shift.sh <project_dir> <issue_number> [agent]}"
ISSUE_NUMBER="${2:?Usage: night_shift.sh <project_dir> <issue_number> [agent]}"
AGENT="${3:-claude}"

PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
BASE_BRANCH="main"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() { echo "[night_shift] $(ts) $*"; }

# An unattended executor must refuse ambiguous input rather than guess at it:
# a non-numeric issue would otherwise reach the API as a nonsense path.
if ! printf '%s' "${ISSUE_NUMBER}" | grep -qE '^[0-9]+$'; then
    log "ABORT — issue number must be numeric, got: ${ISSUE_NUMBER}"
    exit 2
fi

if [ ! -d "${PROJECT_DIR}/.git" ] && [ ! -f "${PROJECT_DIR}/.git" ]; then
    log "ABORT — not a git checkout: ${PROJECT_DIR}"
    exit 2
fi

LOG_DIR="${PROJECT_DIR}/logs"
mkdir -p "${LOG_DIR}"
SHIFT_LOCK="${LOG_DIR}/night_shift.lock"

# Two concurrent runs would race on the branch and the repo lock, so a second
# firing is a clean no-op rather than a corrupt claim.
if [ -f "${SHIFT_LOCK}" ]; then
    log "SKIP — lock file present: ${SHIFT_LOCK}"
    exit 0
fi
echo "$$" > "${SHIFT_LOCK}"

# Always release the shift lock, and return to the base branch only when the
# tree is clean. A dirty tree is left exactly as it is, with a warning: losing
# an agent's uncommitted work is far worse than leaving the repo on a branch.
_night_shift_cleanup() {
    rm -f "${SHIFT_LOCK}"
    cd "${PROJECT_DIR}" 2>/dev/null || return
    if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
        log "WARN — tree is dirty, staying on $(git branch --show-current 2>/dev/null). Nothing discarded."
        return
    fi
    git switch "${BASE_BRANCH}" >/dev/null 2>&1 || true
}
trap _night_shift_cleanup EXIT

cd "${PROJECT_DIR}"

log "start — issue #${ISSUE_NUMBER}, agent ${AGENT}, project ${PROJECT_DIR}"

# start_gitea_issue.py owns every pre-flight that matters: clean tree, no
# competing repo lock, and the issue actually being open and planned. Let it
# refuse rather than duplicating (and drifting from) its rules here.
if ! "${PYTHON_BIN}" scripts/tools/start_gitea_issue.py "${ISSUE_NUMBER}" --agent "${AGENT}"; then
    log "ABORT — start_gitea_issue.py refused issue #${ISSUE_NUMBER}"
    exit 1
fi

BRANCH="$(git branch --show-current)"
log "branch — ${BRANCH}"

# The agent is given the issue number and the repository's own standards, and
# is told to stop at the PR. Merging stays a human act per AGENTS.md, and an
# unattended run is exactly the context where that rule matters most.
AGENT_PROMPT="You are running unattended on ${PROJECT_DIR}, branch ${BRANCH}, for Gitea issue ${ISSUE_NUMBER}.

Read AGENTS.md first and follow it exactly. Work only on this branch. Never commit to ${BASE_BRANCH}, never merge any PR, and never force-push. Push after every commit so the work survives an interruption.

Do not modify the Legacy Pipeline, the Golden Job fixtures, the dfy files under specs, tests/bdd/net-ready.tags, or specs/dafny-ready.tags unless the issue explicitly asks for it and you say so in the PR.

Implement the issue, keep the gates green, and report any gate that cannot run rather than skipping it silently. When done, open a pull request to ${BASE_BRANCH} and stop. Do not merge it."

if ! command -v "${AGENT}" >/dev/null 2>&1; then
    log "ABORT — agent executable not found on PATH: ${AGENT}"
    exit 1
fi

log "launching ${AGENT}"
set +e
"${AGENT}" --permission-mode acceptEdits -p "${AGENT_PROMPT}"
AGENT_EXIT=$?
set -e

log "agent exited ${AGENT_EXIT}"
exit "${AGENT_EXIT}"
