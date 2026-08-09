#!/usr/bin/env python3
"""
Agent Parking Policy — safely park in-progress work on a Gitea issue.

What it does:
    Ports the park_issue runbook from ThePulseProject to this repository.

    Phase 1 — Classify the working tree (via parking_policy.py):
        - Clean:         push branch, update lock heartbeat, post comment.
        - Unstaged only: auto-checkpoint commit (if enabled), then push.
        - Staged:        STOP — agent must not complete a staged commit.
        - Untracked:     STOP — untracked files must be gitignored first.

    Phase 2 — Checkpoint commit (when auto-checkpoint is on):
        Format: checkpoint(agent): parking issue #<N> on <branch>
        Only commits tracked modified files. Never uses git add -A.
        Blocked paths (.env, tokens, bin/, obj/, etc.) are excluded.

    Phase 3 — Push and update:
        - Push the feature branch to the origin remote, which is the canonical Gitea remote.
        - Update heartbeat_at in the lock file.
        - Post [Agent Checkpoint] comment to the Gitea issue.

    Auto-checkpoint is on by default. Disable with:
        AGENT_AUTO_CHECKPOINT=false   (in .env or environment)
        --no-checkpoint               (CLI flag, wins over env)

Why it was created:
    Ported from ThePulseProject Sprint #46 (Agent Parking Policy) — makes it
    safe for an AI agent to preserve work and hand off an issue without losing
    any changes.

How to run:
    python3 scripts/tools/park_gitea_issue.py [--no-checkpoint] [--reason <text>] [--dry-run]

    Examples:
        python3 scripts/tools/park_gitea_issue.py
        python3 scripts/tools/park_gitea_issue.py --reason "blocking dependency found"
        python3 scripts/tools/park_gitea_issue.py --no-checkpoint --dry-run
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import timezone
from typing import NoReturn

# Ensure the tools directory is on the path for sibling imports.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from parking_policy import (
    POLICY_CHECKPOINT,
    POLICY_PROCEED,
    classify_working_tree,
    filter_safe_files,
    tracked_modified_files,
)

# ── Configuration ─────────────────────────────────────────────────────────────

REPO_SLUG = "RTSColonyTerrainGenerator"
GITEA_URL = "http://192.168.2.48:3000"
GITEA_OWNER = "craigpars"
GITEA_REPO = "RTSColonyTerrainGenerator"
GITEA_REMOTE = "origin"

TOKEN_FILE = Path.home() / ".config" / "pulse" / "gitea_token"
LOCK_FILE = Path.home() / ".config" / "pulse" / "locks" / f"{REPO_SLUG}.json"

DEFAULT_REASON = "agent parking work in progress"


# ── Token helper ───────────────────────────────────────────────────────────────


def load_token() -> str:
    """Resolve the Gitea API token from env or file."""
    env_token = os.environ.get("GITEA_TOKEN", "").strip()
    if env_token:
        return env_token

    if TOKEN_FILE.exists():
        file_token = TOKEN_FILE.read_text().strip()
        if file_token:
            return file_token

    die("No Gitea token found. Set GITEA_TOKEN or write it to " + str(TOKEN_FILE))


# ── Git helpers ────────────────────────────────────────────────────────────────


def run_git(args: list[str]) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(["git"] + args, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def current_branch() -> str:
    """Return the current git branch name."""
    code, branch, _ = run_git(["branch", "--show-current"])
    if code != 0 or not branch:
        die("Could not determine current branch.")
    return branch


def current_commit_hash() -> str:
    """Return the short hash of HEAD."""
    code, commit_hash, _ = run_git(["rev-parse", "--short", "HEAD"])
    if code != 0:
        return "unknown"
    return commit_hash


# ── Gitea API helper ───────────────────────────────────────────────────────────


def post_comment(issue_number: int, body: str, token: str) -> None:
    """Post a comment to the Gitea issue."""
    try:
        import requests as req
    except ImportError:
        die("The 'requests' library is required: pip install requests")

    headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
    response = req.post(
        f"{GITEA_URL}/api/v1/repos/{GITEA_OWNER}/{GITEA_REPO}/issues/{issue_number}/comments",
        headers=headers,
        json={"body": body},
        timeout=10,
    )
    if response.status_code not in (200, 201):
        die(f"Failed to post Gitea comment: HTTP {response.status_code}\n{response.text[:200]}")


# ── Error / info helpers ───────────────────────────────────────────────────────


def die(message: str) -> NoReturn:
    """
    Print an error and exit non-zero.

    :param message: Human-readable failure reason for the operator.

    :return: Never returns because the process exits with a non-zero status.
    """
    print(f"✗  {message}", file=sys.stderr)
    sys.exit(1)


def info(message: str, dry_run: bool = False) -> None:
    """Print a status line."""
    prefix = "[DRY RUN] " if dry_run else ""
    print(f"{prefix}{message}")


# ── Auto-checkpoint enabled? ───────────────────────────────────────────────────


def auto_checkpoint_enabled(cli_no_checkpoint: bool) -> bool:
    """
    Determine whether auto-checkpoint is active.

    Priority: CLI --no-checkpoint > AGENT_AUTO_CHECKPOINT env var > default (True).
    """
    if cli_no_checkpoint:
        return False

    env_value = os.environ.get("AGENT_AUTO_CHECKPOINT", "true").strip().lower()
    return env_value not in ("false", "0", "no")


# ── Lock file helpers ──────────────────────────────────────────────────────────


def read_lock_file() -> dict:
    """Read and return the active lock file. Dies if absent or unreadable."""
    if not LOCK_FILE.exists():
        die(
            "No lock file found. There is no active issue claim to park.\n"
            f"Expected: {LOCK_FILE}"
        )
    try:
        return json.loads(LOCK_FILE.read_text())
    except (json.JSONDecodeError, OSError) as parse_error:
        die(f"Lock file is unreadable: {parse_error}")


def update_lock_heartbeat(dry_run: bool) -> None:
    """Write the current timestamp to heartbeat_at in the lock file."""
    now_iso = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    info(f"  → Update lock file heartbeat_at: {now_iso}", dry_run)
    if dry_run:
        return
    lock_data = json.loads(LOCK_FILE.read_text())
    lock_data["heartbeat_at"] = now_iso
    LOCK_FILE.write_text(json.dumps(lock_data, indent=2))
    info("  ✓ Lock file heartbeat updated")


# ── Phase 2: Checkpoint commit ─────────────────────────────────────────────────


def make_checkpoint_commit(
    issue_number: int,
    branch: str,
    reason: str,
    agent_name: str | None,
    dry_run: bool,
) -> str | None:
    """
    Stage tracked modified files and create a checkpoint commit.

    Returns the short commit hash, or None when dry-running.
    Blocked paths (env files, tokens, build outputs) are excluded and reported.
    """
    modified = tracked_modified_files()

    if not modified:
        info("  ✓ No tracked modifications — skipping checkpoint commit")
        return current_commit_hash()

    safe_files, blocked_files = filter_safe_files(modified)

    if blocked_files:
        info(f"  ⚠ Skipping {len(blocked_files)} blocked path(s):")
        for path in blocked_files:
            info(f"      {path}")

    if not safe_files:
        info("  ✓ All modified files are blocked; no checkpoint commit needed")
        return current_commit_hash()

    agent_tag = agent_name if agent_name else "agent"
    timestamp = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    commit_message = (
        f"checkpoint({agent_tag}): {reason} [#{issue_number}]\n\n"
        f"Branch: {branch}\n"
        f"At: {timestamp}"
    )

    info(f"  → Stage {len(safe_files)} file(s) for checkpoint commit", dry_run)
    for path in safe_files:
        info(f"      {path}", dry_run)

    if dry_run:
        info(f"  → Commit: {commit_message.splitlines()[0]}", dry_run)
        return None

    # Stage only the safe tracked files — never git add -A.
    code, _, stderr = run_git(["add", "--"] + safe_files)
    if code != 0:
        die(f"git add failed: {stderr}")

    code, _, stderr = run_git(["commit", "-m", commit_message])
    if code != 0:
        die(f"git commit failed: {stderr}")

    commit_hash = current_commit_hash()
    info(f"  ✓ Checkpoint commit: {commit_hash}")
    return commit_hash


# ── Phase 3: Push and notify ───────────────────────────────────────────────────


def push_branch(branch: str, dry_run: bool) -> None:
    """Push the current branch to the canonical Gitea remote."""
    info(f"  → git push {GITEA_REMOTE} {branch}", dry_run)
    if dry_run:
        return

    code, _, stderr = run_git(["push", GITEA_REMOTE, branch])
    if code != 0:
        die(
            f"Push failed: {stderr}\n"
            "Resolve the push failure before the issue can be safely parked."
        )
    info(f"  ✓ Branch pushed to {GITEA_REMOTE}")


def post_checkpoint_comment(
    issue_number: int,
    branch: str,
    commit_hash: str,
    reason: str,
    token: str,
    dry_run: bool,
) -> None:
    """Post the [Agent Checkpoint] comment to the Gitea issue."""
    now_iso = datetime.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    comment_lines = [
        "[Agent Checkpoint]",
        f"Branch: {branch}",
        f"Commit: {commit_hash}",
        f"Reason: {reason}",
        f"At: {now_iso}",
    ]
    comment_body = "\n".join(comment_lines)

    info(f"  → Post [Agent Checkpoint] comment on #{issue_number}", dry_run)
    if dry_run:
        info(comment_body, dry_run)
        return

    post_comment(issue_number, comment_body, token)
    info("  ✓ Checkpoint comment posted")


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Park in-progress work: checkpoint commit, push, update lock, post comment."
    )
    parser.add_argument(
        "--reason",
        default=DEFAULT_REASON,
        help="Why work is being parked (included in commit message and Gitea comment)",
    )
    parser.add_argument(
        "--no-checkpoint",
        action="store_true",
        dest="no_checkpoint",
        help="Skip the checkpoint commit even when there are unstaged changes",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print every action without mutating any state",
    )
    args = parser.parse_args()

    dry_run: bool = args.dry_run
    reason: str = args.reason

    token = load_token()
    lock_data = read_lock_file()
    issue_number: int = lock_data["issue_number"]
    branch: str = lock_data["branch"]
    agent_name: str | None = lock_data.get("agent")

    info(f"\n=== Parking issue #{issue_number} on branch '{branch}' {'[DRY RUN]' if dry_run else ''} ===")

    # ── Phase 1: Classify dirty state ─────────────────────────────────────────
    info("\n--- Phase 1: Classify working tree ---")
    state = classify_working_tree()
    info(f"  State: {state['category']} → policy: {state['policy']}")

    if state["policy"] == "stop-staged":
        die(state["message"])

    if state["policy"] == "stop-untracked":
        die(state["message"])

    # ── Phase 2: Checkpoint commit ─────────────────────────────────────────────
    info("\n--- Phase 2: Checkpoint ---")
    commit_hash = current_commit_hash()

    if state["policy"] == POLICY_CHECKPOINT:
        if auto_checkpoint_enabled(args.no_checkpoint):
            commit_hash = make_checkpoint_commit(
                issue_number, branch, reason, agent_name, dry_run
            ) or current_commit_hash()
        else:
            info("  ✓ Auto-checkpoint disabled — skipping commit (unstaged changes remain)")
    else:
        info(f"  ✓ Working tree clean — no checkpoint commit needed (HEAD: {commit_hash})")

    # ── Phase 3: Push and update ───────────────────────────────────────────────
    info("\n--- Phase 3: Push and update ---")
    push_branch(branch, dry_run)
    update_lock_heartbeat(dry_run)
    post_checkpoint_comment(issue_number, branch, commit_hash, reason, token, dry_run)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}✓ Issue #{issue_number} parked on '{branch}' at {commit_hash}")
    print("  Lock file is intact. Issue remains claimed by this worker.")
    print("  Resume with: git checkout " + branch)


if __name__ == "__main__":
    main()
