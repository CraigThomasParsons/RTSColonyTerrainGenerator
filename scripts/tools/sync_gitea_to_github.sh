#!/usr/bin/env bash
# scripts/tools/sync_gitea_to_github.sh
#
# What it does:
#   One-way nightly mirror from Gitea to GitHub. Fetches both remotes,
#   fast-forwards main from origin/main (Gitea), then pushes main and
#   tags to github (GitHub). Designed to run as a NAS systemd user
#   service under the account that owns the repository checkout.
#
#   Remote layout in this repo (differs from the AgileMedievalPeasantBoard
#   original, where Gitea was 'gitea' and GitHub was 'origin'):
#     origin -> ssh://git@192.168.2.48:2222/craigpars/RTSColonyTerrainGenerator.git  (Gitea, canonical)
#     github -> git@github.com:CraigThomasParsons/RTSColonyTerrainGenerator.git     (GitHub, mirror)
#
# Why it was created:
#   Ported from AgileMedievalPeasantBoard Sprint #60 (Nightly Gitea To GitHub
#   Mirror). Keeps GitHub current as a read-only backup mirror while Gitea
#   remains the active development forge.
#
# How to run:
#   bash scripts/tools/sync_gitea_to_github.sh
#   # or via systemd on the NAS:
#   systemctl --user start rtscolony-github-mirror.service
#
# Safety rules (never relaxed):
#   - Never uses `git push --force`.
#   - Never uses `git reset --hard`.
#   - Refuses to run from a dirty worktree (exits 0 with a clear log).
#   - Refuses a non-fast-forward update to main (exits 1).
#   - Exits 1 on any failed fetch or push.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

GITEA_REMOTE="origin"
GITHUB_REMOTE="github"
BASE_BRANCH="main"

# ── Helpers ────────────────────────────────────────────────────────────────────

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
}

die() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] FATAL: $*" >&2
    exit 1
}

# ── Main ───────────────────────────────────────────────────────────────────────

log "Starting Gitea -> GitHub mirror from ${REPO_ROOT}"

cd "${REPO_ROOT}" || die "Cannot cd into ${REPO_ROOT}"

# Phase 1: dirty worktree guard — skip without modifying any files.
PORCELAIN_OUTPUT="$(git status --porcelain)"
if [ -n "${PORCELAIN_OUTPUT}" ]; then
    log "SKIP: Working tree is dirty — aborting without push."
    log "Dirty paths:"
    while IFS= read -r dirty_line; do
        log "  ${dirty_line}"
    done <<< "${PORCELAIN_OUTPUT}"
    exit 0
fi
log "Working tree is clean."

# Phase 2: confirm both remotes are configured before touching anything.
for remote_name in "${GITEA_REMOTE}" "${GITHUB_REMOTE}"; do
    git remote get-url "${remote_name}" > /dev/null 2>&1 \
        || die "Remote '${remote_name}' is not configured. Aborting."
done
log "Both remotes (${GITEA_REMOTE}, ${GITHUB_REMOTE}) are present."

# Phase 3: fetch both remotes with ref pruning.
log "Fetching ${GITEA_REMOTE} (with --prune)..."
git fetch "${GITEA_REMOTE}" --prune || die "Failed to fetch remote '${GITEA_REMOTE}'."

log "Fetching ${GITHUB_REMOTE} (with --prune)..."
git fetch "${GITHUB_REMOTE}" --prune || die "Failed to fetch remote '${GITHUB_REMOTE}'."

# Phase 4: fast-forward main from Gitea — never force, never rebase.
log "Checking out ${BASE_BRANCH}..."
git checkout "${BASE_BRANCH}" || die "Cannot checkout ${BASE_BRANCH}."

MAIN_BEFORE="$(git rev-parse HEAD)"
log "${BASE_BRANCH} before sync: ${MAIN_BEFORE}"

log "Fast-forwarding ${BASE_BRANCH} from ${GITEA_REMOTE}/${BASE_BRANCH}..."
git pull --ff-only "${GITEA_REMOTE}" "${BASE_BRANCH}" \
    || die "Cannot fast-forward ${BASE_BRANCH} from ${GITEA_REMOTE}/${BASE_BRANCH}. Has it diverged?"

MAIN_AFTER="$(git rev-parse HEAD)"
if [ "${MAIN_BEFORE}" = "${MAIN_AFTER}" ]; then
    log "${BASE_BRANCH} is already up to date: ${MAIN_AFTER}"
else
    log "${BASE_BRANCH} after sync:  ${MAIN_AFTER}"
fi

# Phase 5: push refs to GitHub. No force push.
log "Pushing ${BASE_BRANCH} to ${GITHUB_REMOTE}..."
git push "${GITHUB_REMOTE}" "${BASE_BRANCH}" || die "Failed to push ${BASE_BRANCH} to ${GITHUB_REMOTE}."

log "Pushing tags to ${GITHUB_REMOTE}..."
git push "${GITHUB_REMOTE}" --tags || die "Failed to push tags to ${GITHUB_REMOTE}."

# Phase 6: summary.
log "Mirror complete."
log "  ${BASE_BRANCH}: ${MAIN_AFTER}"
log "  source: $(git remote get-url "${GITEA_REMOTE}")"
log "  target: $(git remote get-url "${GITHUB_REMOTE}")"
