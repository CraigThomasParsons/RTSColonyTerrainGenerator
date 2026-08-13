#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Launch one supervised agent phase in a detached tmux session.

Usage:
  launch_agent_phase.sh \
    --session NAME \
    --worktree PATH \
    --provider grok|claude \
    --prompt-file PATH \
    [--handoff-from SESSION] \
    [--dry-run]

The launcher refuses protected branches, duplicate session names, missing
prompts/providers, and unacknowledged tmux sessions attached to the worktree.
Use --handoff-from only after the predecessor provider has stopped writing.

Set CLAUDE_ALLOWED_TOOLS to a comma-separated Claude tool allowlist when a
non-interactive phase must run pre-authorized evidence commands. The launcher
keeps acceptEdits as the default and never enables skip-permissions.

Example — issue #37 / PR #45 Claude-to-Grok handoff:
  scripts/tools/launch_agent_phase.sh \
    --session nyx-pr45-grok \
    --worktree /home/craigpar/Code/RTSColonyTerrainGenerator-gui \
    --provider grok \
    --prompt-file scripts/tools/prompts/issue-37-pr-45-simplify-grok.txt \
    --handoff-from mapgui
EOF
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

session=''
worktree=''
provider=''
prompt_file=''
handoff_from=''
dry_run=false

while (($#)); do
    case "$1" in
        --session) session=${2-}; shift 2 ;;
        --worktree) worktree=${2-}; shift 2 ;;
        --provider) provider=${2-}; shift 2 ;;
        --prompt-file) prompt_file=${2-}; shift 2 ;;
        --handoff-from) handoff_from=${2-}; shift 2 ;;
        --dry-run) dry_run=true; shift ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown argument: $1" ;;
    esac
done

[[ -n $session ]] || die '--session is required'
[[ $session =~ ^[A-Za-z0-9_.-]+$ ]] || die 'session contains unsupported characters'
[[ -n $worktree ]] || die '--worktree is required'
[[ -n $provider ]] || die '--provider is required'
[[ -n $prompt_file ]] || die '--prompt-file is required'

command -v git >/dev/null || die 'git is unavailable'
command -v tmux >/dev/null || die 'tmux is unavailable'

worktree=$(realpath -e -- "$worktree")
prompt_file=$(realpath -e -- "$prompt_file")
[[ -d $worktree ]] || die "worktree is not a directory: $worktree"
[[ -s $prompt_file ]] || die "prompt is empty: $prompt_file"
git -C "$worktree" rev-parse --is-inside-work-tree >/dev/null 2>&1 ||
    die "not a git worktree: $worktree"

branch=$(git -C "$worktree" branch --show-current)
[[ -n $branch ]] || die 'detached HEAD is not allowed'
case "$branch" in
    main|master|develop) die "protected branch is not allowed: $branch" ;;
esac

if tmux has-session -t "=$session" 2>/dev/null; then
    die "tmux session already exists: $session"
fi

while IFS=$'\t' read -r existing_session pane_path; do
    [[ -n $existing_session ]] || continue
    [[ $pane_path == "$worktree" ]] || continue
    if [[ -n $handoff_from && $existing_session == "$handoff_from" ]]; then
        continue
    fi
    die "session '$existing_session' is already attached to this worktree"
done < <(tmux list-panes -a -F '#{session_name}\t#{pane_current_path}' 2>/dev/null || true)

case "$provider" in
    grok)
        provider_bin=${GROK_BIN:-/home/craigpar/.grok/bin/grok}
        [[ -x $provider_bin ]] || die "Grok executable is unavailable: $provider_bin"
        provider_command=("$provider_bin" --prompt-file "$prompt_file")
        ;;
    claude)
        provider_bin=${CLAUDE_BIN:-$(command -v claude || true)}
        [[ -n $provider_bin && -x $provider_bin ]] || die 'Claude executable is unavailable'
        if [[ -n ${CLAUDE_ALLOWED_TOOLS:-} ]]; then
            provider_command=(
                "$provider_bin"
                --permission-mode dontAsk
                --allowedTools "$CLAUDE_ALLOWED_TOOLS"
                --print "$(<"$prompt_file")"
            )
        else
            provider_command=("$provider_bin" --permission-mode acceptEdits --print "$(<"$prompt_file")")
        fi
        ;;
    *) die "unsupported provider: $provider" ;;
esac

launch_command=(
    tmux new-session -d -s "$session" -x 220 -y 50 -c "$worktree"
    "${provider_command[@]}"
    ';' set-option -t "$session" remain-on-exit on
)

printf 'session: %s\nworktree: %s\nbranch: %s\nprovider: %s\nprompt: %s\n' \
    "$session" "$worktree" "$branch" "$provider" "$prompt_file"
if [[ -n $handoff_from ]]; then
    printf 'handoff-from: %s\n' "$handoff_from"
fi

if $dry_run; then
    printf 'command:'
    printf ' %q' "${launch_command[@]}"
    printf '\n'
    exit 0
fi

"${launch_command[@]}"
printf 'launched: %s\ninspect: tmux capture-pane -pt %q -S -160\n' "$session" "$session"
printf 'receipt retention: remain-on-exit enabled\n'
