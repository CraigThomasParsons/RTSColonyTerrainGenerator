#!/usr/bin/env bash
set -euo pipefail

# Resume the long-running Codex conversation that established the repository's
# Gitea, Nyx, PixelLab, map-detailing, and remote-workstation context.
readonly SESSION_ID='019fe22c-758a-7503-b9c4-e8aad8fc39eb'
readonly REPOSITORY_ROOT='/home/craigpar/Code/RTSColonyTerrainGenerator'

usage() {
    cat <<'EOF'
Resume the pinned RTSColonyTerrainGenerator Codex session.

Usage:
  scripts/sessions/resume_rtscolony_codex.sh
  scripts/sessions/resume_rtscolony_codex.sh "Optional message for Codex"
  scripts/sessions/resume_rtscolony_codex.sh --print-id

The script always resumes the exact recorded session from the canonical
repository directory. Any remaining arguments are joined into one initial
message for the resumed session.
EOF
}

case "${1-}" in
    --help|-h)
        usage
        exit 0
        ;;
    --print-id)
        printf '%s\n' "$SESSION_ID"
        exit 0
        ;;
esac

command -v codex >/dev/null 2>&1 || {
    printf 'error: codex is not available on PATH\n' >&2
    exit 1
}

[[ -d "$REPOSITORY_ROOT/.git" ]] || {
    printf 'error: repository is unavailable: %s\n' "$REPOSITORY_ROOT" >&2
    exit 1
}

if (($# > 0)); then
    exec codex resume \
        --include-non-interactive \
        --cd "$REPOSITORY_ROOT" \
        "$SESSION_ID" \
        "$*"
fi

exec codex resume \
    --include-non-interactive \
    --cd "$REPOSITORY_ROOT" \
    "$SESSION_ID"
